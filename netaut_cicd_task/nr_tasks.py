from nornir.core import Nornir
from nornir.core.task import Result, Task
from nornir.core.filter import F
from nornir_netconf.plugins.tasks import netconf_get_config
from nornir_jinja2.plugins.tasks import template_file

from netaut_cicd_task.filter import split_interface, first_host, networkmask

finja_filter = {
    "split_interface": split_interface,
    "first_host": first_host,
    "networkmask": networkmask,
}


def get_vrf_ospf_bgp(task: Task) -> Result:
    subtree_filter = """<native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
        <vrf/>
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

    return task.run(
        netconf_get_config,
        source="running",
        path=subtree_filter,
        filter_type="subtree",
    )


def desired_rpc(task: Task, nr: Nornir) -> Result:
    rr_hosts = nr.filter(F(tags__contains="RR")).inventory.hosts
    edge_hosts = nr.filter(F(tags__contains="edge")).inventory.hosts
    native = task.run(
        template_file,
        template="native.j2",
        path="templates",
        jinja_filters=finja_filter,
        rr_hosts=rr_hosts,
        edge_hosts=edge_hosts,
    )
    return native
