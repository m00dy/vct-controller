import re
from optparse import make_option

from django.core.management.base import BaseCommand

from controller.utils.system import run, check_root


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.option_list = BaseCommand.option_list + (
            make_option('--minimal', action='store_true', dest='minimal', default=False,
                help='Only install minimal requirements'),
            make_option('--specifics', action='store_true', dest='specifics_only', default=False,
                help='Only run version specific operations'),
            make_option('--from', dest='version', default=False,
                help="Controller's version from where you are upgrading, i.e 0.6.32"),
            )
    
    option_list = BaseCommand.option_list
    help = 'Upgrades confine-controller installation'
    can_import_settings = False
    
    @check_root
    def handle(self, *args, **options):
        if not options.get('specifics_only'):
            # Common stuff
            minimal = options.get('minimal')
            
            if minimal:
                run("controller-admin.sh install_requirements --minimal")
            else:
                run("controller-admin.sh install_requirements")
                run("python manage.py collectstatic --noinput")
            
            run("python manage.py syncdb")
            run("python manage.py migrate")
            run("python manage.py restartservices")
        
        # Version specific
        version = options.get('version')
        if not version:
            self.stderr.write('\nNext time you migth want to provide a --from argument '
                              'in order to run version specific upgrade operations\n')
            return
        
        version_re = re.compile(r'^\s*(\d+)\.(\d+)\.(\d+).*')
        major, major2, minor = version_re.search(version).groups()
        # Represent version as two digits per number: 1.2.2 -> 10202
        version = int(str(major) + "%02d" % int(major2) + "%02d" % int(minor))
        if version <= 629:
            # Clean existing sessions because of change on auth backend
            run('echo "delete from django_session;" | python manage.py dbshell')