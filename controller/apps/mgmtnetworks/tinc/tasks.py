from subprocess import Popen, PIPE
import os, glob

from celery.task import task

from nodes.models import Server

from .settings import TINC_NET_NAME


@task(name="tinc.update_tincd")
def update_tincd():
    """
    Generates all local tinc/hosts/* and reloads tincd
    """
    from .models import TincClient
    
    server = Server.objects.get().tinc
    db_clients = list(TincClient.objects.all())
    db_clients += list(TincClient.objects.all())
    hosts_path = '/etc/tinc/%s/hosts/' % TINC_NET_NAME
    
    # create bash script for generating clients host files
    script = ''
    for client in db_clients:
        host_file = os.path.join(hosts_path, client.name)
        script += 'echo -e "%s" > %s;' % (client.get_host(), host_file)
    
    # delete all tinc hosts
    sys_clients = glob.glob(os.path.join(hosts_path, 'host_*'))
    sys_clients.extend(glob.glob(os.path.join(hosts_path, 'node_*')))
    for client in sys_clients:
        try:
            os.remove(client)
        except OSError:
            pass
    
    # create all tinc hosts
    if script != '':
        cmd = Popen(script, shell=True, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = cmd.communicate()
        if cmd.returncode > 0:
            raise TincClient.UpdateTincdError(stderr)
        
        # reload tincd in a separated command to prevent clients from losing its
        # connection when something goes wrong
        cmd = Popen("/etc/init.d/tinc reload", shell=True, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = cmd.communicate()
        if cmd.returncode > 0:
            raise TincClient.UpdateTincdError(stderr)