import typer
from logging import DEBUG, INFO
from rich.console import Console
from nornir import InitNornir
# from nornir_utils.plugins.functions import print_result
from nornir_rich.functions import print_result

from netaut_cicd_task.nr_tasks import get_vrf_ospf_bgp, desired_rpc, deploy_config

app = typer.Typer()
console = Console()


@app.callback()
def get_nornir(
    ctx: typer.Context,
    configuration_file: typer.FileText = typer.Option(
        "config.yaml",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        metavar="NORNIR_SETTINGS",
        help="Path to the nornir configuration file.",
        envvar="NORNIR_SETTINGS",
    ),
    pod_number: int = typer.Option(
        ...,
        help="Pod number to use.",
        metavar="LAB_POD_NUMBER",
        envvar="LAB_POD_NUMBER",
    ),
) -> None:
    """
    Get nornir object from configuration file
    """

    deploy = ctx.invoked_subcommand == "deploy"
    nr = InitNornir(config_file=str(configuration_file), dry_run=not deploy)

    # Hack to set the hostnames according to the pod number
    for host in nr.inventory.hosts:
        nr.inventory.hosts[host].hostname = f"{host}-pod-{pod_number}.network.garden"
    ctx.obj = nr


@app.command()
def get_config(ctx: typer.Context) -> None:
    """Get XML"""
    nr = ctx.obj
    print_result(nr.run(task=get_vrf_ospf_bgp))
    console.print("RPCs")


@app.command()
def validate(ctx: typer.Context, debug: bool = False) -> None:
    """Load configuration into candidate store and exit with validate"""
    nr = ctx.obj
    result = nr.run(task=deploy_config)
    print_result(result, severity_level=DEBUG if debug else INFO)
    if result.failed:
        console.print("Validation failed")
        raise typer.Exit(code=1)
    console.print("Validation successful")
    raise typer.Exit(code=0)


@app.command()
def deploy(ctx: typer.Context, debug: bool = False) -> None:
    """Deploy configuration into running store"""
    nr = ctx.obj
    result = nr.run(task=deploy_config)
    print_result(result, severity_level=DEBUG if debug else INFO)
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
    print_result(nr.run(task=desired_rpc))


if __name__ == "__main__":
    app()
