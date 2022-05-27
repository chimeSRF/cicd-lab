# NetAut CI/CD Demo Project


## Topology

```mermaid
graph LR
    subgraph 100.64.255.3
        sw03(sw03)
    end
    subgraph 100.64.255.4
        sw04(sw04)
    end
    subgraph core
        subgraph 100.64.255.1
            RR{{RR}}
            sw01((sw01))
        end
        subgraph 100.64.255.2
            sw02((sw02))
        end
    end
    sw03 -- ip unnumberd --- sw01 & sw02 -- ip unnumberd --- sw04
    
    sw01 -- ip unnumber --- sw02
    
    pc1{PC01} -- access ports --- sw03
    sw04 -- access ports --- pc2{PC02}
```

**Note:** With `ip unnumberd` the interface itself does not need an IP address on the point-to-point links. Because we don't have an IPAM this makes the inventory easier.
{: .note}

## Environment Variable


```
NORNIR_PASSWORD=*****       # password for the user ins
NORNIR_SETTINGS=config.yaml # Path to nornir settings file
LAB_POD_NUMBER=9            # INS Pod number
```


# ToDo

Create the CI/CD pipeline
