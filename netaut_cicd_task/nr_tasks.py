from nornir.core.task import Result, Task
from nornir_netconf.plugins.tasks import netconf_get_config


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


def configure(task: Task, candidate: bool = True):
    ...

    # ToDo: Send OSPF config

    # ToDo: Send VRF config

    # ToDo: Send BGP config

    # ToDo: Send interface config
