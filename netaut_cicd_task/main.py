import typer
from rich.console import Console
from nornir import InitNornir
from nornir_utils.plugins.functions import print_result

from netaut_cicd_task.nr_tasks import get_vrf_ospf_bgp, desired_rpc, edit_config

app = typer.Typer()
console = Console()


@app.callback()
def get_nornir(
    ctx: typer.Context,
    configuration_file: typer.FileText = typer.Option(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        metavar="NORNIR_SETTINGS",
        help="Path to the nornir configuration file.",
    ),
    pod_number: int = typer.Option(
        ..., help="Pod number to use.", metavar="LAB_POD_NUMBER"
    ),
) -> None:
    """
    Get nornir object from configuration file
    """
    nr = InitNornir(config_file=str(configuration_file))

    # Hack to set the hostnames according to the pod number
    for host in nr.inventory.hosts:
        nr.inventory.hosts[host].hostname = f"{host}-pod-{pod_number}.lab.ins.hsr.ch"
    ctx.obj = nr


@app.command()
def get_config(ctx: typer.Context) -> None:
    """Get XML"""
    nr = ctx.obj
    print_result(nr.run(task=get_vrf_ospf_bgp))
    console.print("RPCs")


@app.command()
def validate(ctx: typer.Context) -> None:
    """Load configuration into candidate store and exit with validate"""
    nr = ctx.obj
    result = nr.run(task=edit_config, nr=nr, candidate=True)
    print_result(result)
    if result.failed:
        console.print("Validation failed")
        raise typer.Exit(code=1)
    console.print("Validation successful")
    raise typer.Exit(code=0)


@app.command()
def deploy(ctx: typer.Context) -> None:
    """Deploy configuration into running store"""
    nr = ctx.obj
    result = nr.run(task=edit_config, nr=nr, candidate=False)
    print_result(result)
    print(f"Failed hosts: {result.failed_hosts}")
    if result.failed:
        console.print("Deployment failed")
        raise typer.Exit(code=1)
    console.print("Deployment successful")
    raise typer.Exit(code=0)


@app.command()
def desired_state(ctx: typer.Context) -> None:
    """Get desired state"""
    nr = ctx.obj
    print_result(nr.run(task=desired_rpc, nr=nr))


if __name__ == "__main__":
    app()
