from typing import Tuple
from ipaddress import ip_network


def split_interface(interface: str) -> Tuple[str, str]:
    """
    Split interface name into interface type and interface number.
    """
    finds = [interface.find(str(x)) for x in range(10)]
    first_digit = min(filter(lambda x: x > -1, finds))
    return interface[:first_digit], interface[first_digit:]


def first_host(network: str) -> str:
    """
    Get first host in network.
    """
    return str(next(ip_network(network).hosts()))


def networkmask(network: str) -> str:
    """
    Get network mask from network.
    """
    return str(ip_network(network).netmask)
