from logging import DEBUG
from typing import List
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


def netconf_lock(task: Task, target: str) -> Result:
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    rpc = manager.lock(target=target)
    result = {
        "error": rpc.error,
        "errors": rpc.errors,
        "ok": rpc.ok,
        "rpc": rpc,
    }
    return Result(host=task.host, result=result, failed=not rpc.ok)


def netconf_unlock(task: Task, target: str) -> Result:
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    rpc = manager.unlock(target=target)
    result = {
        "error": rpc.error,
        "errors": rpc.errors,
        "ok": rpc.ok,
        "rpc": rpc,
    }
    return Result(host=task.host, result=result, failed=not rpc.ok)


def netconf_edit_config(task: Task, target: str, default_operation: str, config: str) -> Result:
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    rpc = manager.edit_config(
        config,
        target=target,
        default_operation=default_operation
    )
    result = {
        "error": rpc.error,
        "errors": rpc.errors,
        "ok": rpc.ok,
        "rpc": rpc,
    }
    return Result(host=task.host, result=result, failed=not rpc.ok)


def netconf_get_config(task: Task, source: str, models: List) -> Result:
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    loaded_models = manager.models_loaded
    available_models = manager.models_loadable

    if not set(models).issubset(set(available_models)):
        raise("not all models are part of available models")

    for m in models:
        if m not in loaded_models:
            manager.load_model(m)

    rpc = manager.get_config(
        models=models,
        source=source
    )
    result = {
        "error": rpc.error,
        "errors": rpc.errors,
        "ok": rpc.ok,
        "rpc": rpc,
    }
    return Result(host=task.host, result=result, failed=not rpc.ok)


def netconf_commit(task: Task) -> Result:
    manager = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    rpc = manager.commit()
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
    is_changed = True

    empty_diff = '<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"/>'

    if (str(delta)).strip() == empty_diff:
        delta = "No diff"
        is_changed = False

    return Result(task.host, result=str(delta), failed=False, changed=is_changed)


def deploy_config(task: Task) -> None:
    desired_result = task.run(desired_rpc, severity_level=DEBUG)
    task.run(discard_config, severity_level=DEBUG)

    m = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    task.run(netconf_lock, target="candidate", severity_level=DEBUG)

    task.run(
        netconf_edit_config,
        config=desired_result[0].result,
        target="candidate",
        default_operation="merge",
        severity_level=DEBUG
    )

    candidate_result = task.run(
        netconf_get_config,
        models=['Cisco-IOS-XE-native'],
        source="candidate",
        severity_level=DEBUG
    )

    if not task.is_dry_run():
        task.run(netconf_commit, severity_level=DEBUG)
    else:
        task.run(netconf_validate, severity_level=DEBUG)

        running_result = task.run(
            netconf_get_config,
            models=['Cisco-IOS-XE-native'],
            source="running",
            severity_level=DEBUG
        )
        task.run(
            diff,
            running=m.extract_config(running_result.result['rpc']),
            candidate=m.extract_config(candidate_result.result['rpc'])
        )
    
    task.run(netconf_unlock, target="candidate", severity_level=DEBUG)
