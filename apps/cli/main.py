
import click
import requests
import json
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()
API_BASE = "http://127.0.0.1:18002"

def handle_response(resp):
    try:
        data = resp.json()
        if resp.status_code >= 400:
            console.print(f"[bold red]Error ({resp.status_code}):[/bold red] {data.get('detail', 'Unknown error')}")
            return None
        return data
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to parse response: {str(e)}")
        return None

@click.group()
def cli():
    """SSH Gateway Platform CLI Tool"""
    pass

@cli.command()
@click.argument('username')
@click.argument('password')
def register(username, password):
    """Register a new user"""
    try:
        resp = requests.post(f"{API_BASE}/auth/register", json={"username": username, "password": password})
        data = handle_response(resp)
        if data:
            console.print(f"[bold green]Success:[/bold green] {data.get('message')}")
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

@cli.command()
@click.argument('username')
@click.argument('password')
@click.option('--mfa', help="MFA Code (if enabled)")
def login(username, password, mfa):
    """Login to the platform"""
    try:
        payload = {"username": username, "password": password}
        if mfa:
            payload["mfa_code"] = mfa
        
        resp = requests.post(f"{API_BASE}/auth/login", json=payload)
        data = handle_response(resp)
        if data:
            if data.get('detail') == "MFA_REQUIRED":
                console.print("[yellow]MFA Required![/yellow] Please login again with --mfa option.")
            else:
                console.print(f"[bold green]Login Successful![/bold green]")
                console.print(f"Token: [cyan]{data.get('token')}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

@cli.command()
@click.option('--host', required=True, help="SSH Server Host")
@click.option('--port', default=22, help="SSH Server Port")
@click.option('--user', required=True, help="SSH Username")
@click.option('--pwd', required=True, help="SSH Password")
@click.option('--local-port', required=True, type=int, help="Local Port to listen on")
@click.option('--remote-host', required=True, help="Remote Host to forward to")
@click.option('--remote-port', required=True, type=int, help="Remote Port to forward to")
@click.option('--api-user', default="user", help="API User for ACL/Audit")
def create_tunnel(host, port, user, pwd, local_port, remote_host, remote_port, api_user):
    """Create a local port forwarding tunnel"""
    data = {
        "ssh_host": host,
        "ssh_port": port,
        "username": user,
        "password": pwd,
        "local_port": local_port,
        "remote_host": remote_host,
        "remote_port": remote_port,
        "type": "local"
    }
    try:
        resp = requests.post(f"{API_BASE}/tunnel/create", json=data, headers={"X-User": api_user})
        res_data = handle_response(resp)
        if res_data:
            console.print(f"[bold green]Tunnel Created![/bold green] ID: [cyan]{res_data.get('tunnel_id')}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

@cli.command()
@click.option('--host', required=True, help="SSH Server Host")
@click.option('--port', default=22, help="SSH Server Port")
@click.option('--user', required=True, help="SSH Username")
@click.option('--pwd', required=True, help="SSH Password")
@click.option('--local-port', required=True, type=int, help="Local Port for SOCKS5")
@click.option('--api-user', default="user", help="API User for ACL/Audit")
def create_socks(host, port, user, pwd, local_port, api_user):
    """Create a dynamic SOCKS5 proxy tunnel"""
    data = {
        "ssh_host": host,
        "ssh_port": port,
        "username": user,
        "password": pwd,
        "local_port": local_port,
        "type": "socks5"
    }
    try:
        resp = requests.post(f"{API_BASE}/tunnel/create", json=data, headers={"X-User": api_user})
        res_data = handle_response(resp)
        if res_data:
            console.print(f"[bold green]SOCKS5 Proxy Created![/bold green] ID: [cyan]{res_data.get('tunnel_id')}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

@cli.command()
@click.argument('tunnel_id')
@click.option('--api-user', default="user", help="API User for ACL/Audit")
def stop_tunnel(tunnel_id, api_user):
    """Stop an active tunnel"""
    try:
        resp = requests.post(f"{API_BASE}/tunnel/stop/{tunnel_id}", headers={"X-User": api_user})
        data = handle_response(resp)
        if data:
            console.print(f"[bold yellow]{data.get('message')}[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

@cli.command()
def list_tunnels():
    """List all active tunnels"""
    try:
        resp = requests.get(f"{API_BASE}/tunnel/list")
        data = handle_response(resp)
        if data:
            tunnels = data.get('tunnels', [])
            if not tunnels:
                console.print("[yellow]No active tunnels.[/yellow]")
                return
            
            table = Table(title="Active SSH Tunnels")
            table.add_column("ID", style="cyan")
            table.add_column("Local Port", style="green")
            table.add_column("Type", style="magenta")
            
            for t in tunnels:
                table.add_row(t['id'][:13] + "...", str(t['local_port']), t['type'])
            
            console.print(table)
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

@cli.command()
@click.argument('tunnel_id')
@click.argument('local_port', type=int)
@click.option('--api-user', default="user", help="API User for ACL/Audit")
def verify(tunnel_id, local_port, api_user):
    """Verify if a tunnel is working"""
    try:
        resp = requests.post(f"{API_BASE}/tunnel/verify/{tunnel_id}?local_port={local_port}", headers={"X-User": api_user})
        data = handle_response(resp)
        if data:
            if data.get('success'):
                console.print(f"[bold green]Verification Success![/bold green] Tunnel {tunnel_id} is active.")
            else:
                console.print(f"[bold red]Verification Failed![/bold red] Tunnel {tunnel_id} might be broken.")
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

@cli.command()
@click.argument('tunnel_id')
@click.argument('command')
@click.option('--api-user', default="user", help="API User for ACL/Audit")
def exec(tunnel_id, command, api_user):
    """Execute a command on a tunnel's SSH connection"""
    try:
        resp = requests.post(
            f"{API_BASE}/tunnel/exec/{tunnel_id}", 
            json={"command": command},
            headers={"X-User": api_user}
        )
        data = handle_response(resp)
        if data:
            console.print(f"[bold green]Output:[/bold green]")
            console.print(data.get('output'))
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    cli()
