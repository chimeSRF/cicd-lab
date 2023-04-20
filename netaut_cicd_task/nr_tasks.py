from logging import DEBUG
from nornir.core.task import Task, Result, MultiResult
from nornir.core.filter import F

from netaut_cicd_task.filter import split_interface, first_host, networkmask

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ncdiff import ConfigDelta, Config
from netaut_cicd_task.plugins.connections import CONNECTION_NAME

finja_filter = {
    "split_interface": split_interface,
    "first_host": first_host,
    "networkmask": networkmask,
}


def discard_config(
    task: Task,
) -> Result:
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    rpc = manager.discard_changes()
    result = {
        "error": rpc.error,
        "errors": rpc.errors,
        "ok": rpc.ok,
        "rpc": rpc,
    }
    return Result(host=task.host, result=result, failed=not rpc.ok)


def netconf_validate(
    task: Task,
) -> Result:
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    rpc = manager.validate()
    result = {
        "error": rpc.error,
        "errors": rpc.errors,
        "ok": rpc.ok,
        "rpc": rpc,
    }
    return Result(host=task.host, result=result, failed=not rpc.ok)


def get_vrf_ospf_bgp(task: Task) -> None:
    subtree_filter = """<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
        <vrf/>
        <vlan/>
        <interface>
          <GigabitEthernet/>
          <Loopback/>
          <Vlan/>
        </interface>
        <router>
          <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-bgp"/>
          <router-ospf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ospf"/>
        </router>
      </native>"""

    m = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    m.load_model('Cisco-IOS-XE-native')

    filter_type = "subtree"

    rpc = m.get_config(filter=(filter_type, subtree_filter))
    config = m.extract_config(rpc)

    return Result(host=task.host, result=str(config), failed=not rpc.ok)


def desired_rpc(task: Task) -> None:
    nr = task.nornir
    rr_hosts = nr.filter(F(tags__contains="RR")).inventory.hosts  # type: ignore
    edge_hosts = nr.filter(F(tags__contains="edge")).inventory.hosts  # type: ignore

    env = Environment(
        loader=FileSystemLoader("templates"), undefined=StrictUndefined, trim_blocks=True,
    )
    env.filters.update(finja_filter)
    t = env.get_template("native.j2")
    config = t.render(host=task.host, rr_hosts=rr_hosts, edge_hosts=edge_hosts)

    return Result(host=task.host, result=config)


def diff(task: Task, running: Config, candidate: Config) -> Result:
    delta = ConfigDelta(config_src=running, config_dst=candidate)

    return Result(task.host, result=str(delta) or "No diff", failed=False)


def edit_config(task: Task) -> None:
    desired_result = task.run(desired_rpc, severity_level=DEBUG)
    task.run(discard_config, severity_level=DEBUG)

    m = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    rpc_lock = m.lock(target="candidate")
    assert(rpc_lock.ok)

    rpc_edit_can = m.edit_config(
        desired_result[0].result,
        target="candidate",
        default_operation="merge"
    )
    assert(rpc_edit_can.ok)


    m.load_model('Cisco-IOS-XE-native')
    candidate = m.get_config(
        models=['Cisco-IOS-XE-native'],
        source="candidate",
    )
    assert(candidate.ok)

    if not task.is_dry_run():
        rpc_com = m.commit()
        assert(rpc_com.ok)
    else:
        task.run(netconf_validate)

        running = m.get_config(
            models=['Cisco-IOS-XE-native'],
            source="running",
        )
        assert(running.ok)

        task.run(diff, running=m.extract_config(running), candidate=m.extract_config(candidate))
    
    rpc_unlock = m.unlock(target="candidate")
    assert(rpc_unlock.ok)
