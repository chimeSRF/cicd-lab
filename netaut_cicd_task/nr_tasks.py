from logging import DEBUG
from nornir.core import Nornir
from nornir.core.task import Task, Result, MultiResult
from nornir.core.filter import F
from nornir_netconf.plugins.tasks import (
    netconf_get_config,
    netconf_edit_config,
    netconf_commit,
    netconf_lock,
)
from nornir_jinja2.plugins.tasks import template_file
from xmldiff import main as xmldiff_main

from netaut_cicd_task.filter import split_interface, first_host, networkmask

finja_filter = {
    "split_interface": split_interface,
    "first_host": first_host,
    "networkmask": networkmask,
}


def discard_config(
    task: Task,
) -> Result:
    manager = task.host.get_connection("netconf", task.nornir.config)
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
    manager = task.host.get_connection("netconf", task.nornir.config)
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

    task.run(
        netconf_get_config,
        source="running",
        path=subtree_filter,
        filter_type="subtree",
    )


def desired_rpc(task: Task, nr: Nornir) -> None:
    rr_hosts = nr.filter(F(tags__contains="RR")).inventory.hosts  # type: ignore
    edge_hosts = nr.filter(F(tags__contains="edge")).inventory.hosts  # type: ignore
    task.run(
        template_file,
        template="native.j2",
        path="templates",
        jinja_filters=finja_filter,
        rr_hosts=rr_hosts,
        edge_hosts=edge_hosts,
    )


def diff(task: Task, running: MultiResult, candidate: MultiResult) -> Result:
    diff_options = {
        "F": 0.5,
        "uniqueattrs": [
            "{http://www.w3.org/XML/1998/namespace}id",
            "{http://cisco.com/ns/yang/Cisco-IOS-XE-native}name",
        ],
    }

    diff = xmldiff_main.diff_trees(
        running[0].result["rpc"].data,  # type: ignore
        candidate[0].result["rpc"].data,  # type: ignore
        diff_options=diff_options,
    )

    return Result(task.host, result=diff, failed=False)


def edit_config(task: Task, nr: Nornir) -> None:
    desired_result = task.run(desired_rpc, nr=nr, severity_level=DEBUG)
    task.run(discard_config, severity_level=DEBUG)
    task.run(
        netconf_lock,
        datastore="candidate",
        operation="lock",
        severity_level=DEBUG,
        name="lock_candidate",
    )
    task.run(
        netconf_edit_config,
        config=desired_result[1].result,
        target="candidate",
        severity_level=DEBUG,
    )
    subtree_filter = (
        """<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native"></native>"""
    )
    candidate = task.run(
        netconf_get_config,
        source="candidate",
        path=subtree_filter,
        filter_type="subtree",
        severity_level=DEBUG,
        name="netconf_get_config_candidate",
    )
    if not task.is_dry_run():
        task.run(netconf_commit)
    else:
        task.run(netconf_validate)
        running = task.run(
            netconf_get_config,
            source="running",
            path=subtree_filter,
            filter_type="subtree",
            severity_level=DEBUG,
            name="netconf_get_config_running",
        )
        task.run(diff, running=running, candidate=candidate)
    task.run(
        netconf_lock,
        datastore="candidate",
        operation="unlock",
        severity_level=DEBUG,
        name="unlock_candidate",
    )
