from django_extensions.db import fields
from django_transaction_signals import defer
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from singleton_models.models import SingletonModel

from common.validators import validate_prop_name, validate_net_iface_name

from . import settings, ssl
from .utils import get_mgmt_backend
from .validators import validate_sliver_mac_prefix, validate_ipv4_range, validate_dhcp_range


class Node(models.Model):
    """
    Describes a node in the testbed.
    
    See Node architecture: http://wiki.confine-project.eu/arch:node
    """
    DEBUG = 'debug'
    FAILURE = 'failure'
    SAFE = 'safe'
    PRODUCTION = 'production'
    STATES = (
        (DEBUG, 'Debug'),
        (SAFE, 'Safe'),
        (PRODUCTION, 'Production'),
        (FAILURE, 'Failure'),
    )
    IPV6_METHODS = (
        ('none', 'none'),
        ('dhcp', 'dhcp'),
        ('auto', 'auto'),
    )
    IPV4_METHODS = (
        ('none', 'none'),
        ('dhcp', 'dhcp'),
        ('range', 'range'),
    )
    
    name = models.CharField(max_length=256, unique=True,
        help_text='A unique name for this node. A single non-empty line of '
                  'free-form text with no whitespace surrounding it. matching '
                  'the regular expression',
        validators=[validators.RegexValidator('^[\w.@+-]+$', 
                    'Enter a valid name.', 'invalid')])
    cert = models.TextField('Certificate', unique=True, null=True, blank=True, 
        help_text='X.509 PEM-encoded certificate for this RD. The certificate '
                  'may be signed by a CA recognised in the testbed and required '
                  'by clients and services accessing the node API.')
    description = models.TextField(blank=True,
        help_text='Free-form textual description of this host/device.')
    arch = models.CharField('Architecture', max_length=16,
        choices=settings.NODES_NODE_ARCHS, default=settings.NODES_NODE_ARCH_DFLT,
        help_text='Architecture of this RD (as reported by uname -m).',)
    local_iface = models.CharField('Local Interface', max_length=16, 
        default=settings.NODES_NODE_LOCAL_IFACE_DFLT, 
        validators=[validate_net_iface_name],
        help_text='Name of the interface used as a local interface. See <a href='
                  '"wiki.confine-project.eu/arch:node">node architecture</a>.')
    sliver_pub_ipv6 = models.CharField('Sliver Public IPv6', max_length=8,
        help_text='Indicates IPv6 support for public sliver interfaces in the '
                  'local network (see <a href="https://wiki.confine-project.eu/'
                  'arch:node">node architecture</a>). Possible values: none (no '
                  'public IPv6 support), dhcp (addresses configured using DHCPv6), '
                  'auto (addresses configured using NDP stateless autoconfiguration).',
        default='none', choices=IPV6_METHODS)
    sliver_pub_ipv4 = models.CharField('Sliver Public IPv4', max_length=8,
        help_text='Indicates IPv4 support for public sliver interfaces in the '
                  'local network (see <a href="https://wiki.confine-project.eu/'
                  'arch:node">node architecture</a>). Possible values: none (no '
                  'public IPv4 support), dhcp (addresses configured using DHCP), '
                  'range (addresses chosen from a range, see sliver_pub_ipv4_range).',
        default='none', choices=IPV4_METHODS)
    sliver_pub_ipv4_range = models.CharField('Sliver Public IPv4 Range', 
        help_text='Describes the public IPv4 range that can be used by sliver '
                  'public interfaces. If /sliver_pub_ipv4 is none, its value is '
                  'null. If /sliver_pub_ipv4 is dhcp, its value is #N, where N '
                  'is the decimal integer number of DHCP addresses reserved for '
                  'slivers. If /sliver_pub_ipv4 is range, its value is BASE_IP#N, '
                  'where N is the decimal integer number of consecutive addresses '
                  'reserved for slivers after and including the range\'s base '
                  'address BASE_IP (an IP address in the local network).',
        max_length=256, blank=True, null=True)
    sliver_mac_prefix = models.CharField('Sliver MAC Prefix', null=True,
        blank=True, max_length=5, validators=[validate_sliver_mac_prefix],
        help_text='A 16-bit integer number in 0x-prefixed hexadecimal notation '
                  'used as the node sliver MAC prefix. See <a href="http://wiki.'
                  'confine-project.eu/arch:addressing">addressing</a> for legal '
                  'values. %s when null.</a>.' % settings.NODES_SLIVER_MAC_PREFIX_DFLT)
    priv_ipv4_prefix = models.GenericIPAddressField('Private IPv4 Prefix', 
        protocol='IPv4', null=True, blank=True,
        help_text='IPv4 /24 network in CIDR notation used as a node private IPv4 '
                  'prefix. See <a href="http://wiki.confine-project.eu/arch:'
                  'addressing">addressing</a> for legal values. %s When null.' 
                  % settings.NODES_PRIV_IPV4_PREFIX_DFLT)
    boot_sn = models.IntegerField('Boot Sequence Number', default=0, blank=True, 
        help_text='Number of times this RD has been instructed to be rebooted.')
    set_state = models.CharField(max_length=16, choices=STATES, default=DEBUG,
        help_text='The state set on this node (set state). Possible values: debug '
                  '(initial), safe, production, failure. To support the late '
                  'addition or generation of node keys, the set state is forced '
                  'to remain debug while the node is missing some key, certificate '
                  'or other configuration item. The set state is automatically '
                  'changed to safe when all items are in place. Changing existing '
                  'keys also moves the node into state debug or safe as appropriate. '
                  'All set states but debug can be manually selected. See <a href='
                  '"https://wiki.confine-project.eu/arch:node-states">node states</a> '
                  'for the full description of set states and possible transitions.')
    group = models.ForeignKey('users.Group', related_name='nodes',
        help_text='The group this node belongs to. The user creating this node '
                  'must be an administrator or technician of this group, and the '
                  'group must have node creation allowed (/allow_nodes=true). '
                  'Administrators and technicians in this group are able to '
                  'manage this node.')
    
    def __unicode__(self):
        return self.name
    
    def clean(self):
        # clean set_state:
        old = Node.objects.filter(pk=self.pk)
        if old.exists():
            old = old.get()
            if old.set_state == Node.DEBUG and self.set_state != Node.DEBUG:
                raise ValidationError("Can not manually exit from Debug state.")
            elif self.set_state == Node.DEBUG and old.set_state != Node.DEBUG:
                raise ValidationError("Can not manually enter to Debug state.")
            elif self.set_state == Node.PRODUCTION and old.set_state != Node.SAFE:
                raise ValidationError("Can not make changes nor  manually enter to "
                                      "Production state from another state different "
                                      "than Safe.")
        elif self.set_state != Node.DEBUG:
            raise ValidationError("Initial state must be Debug")
        # clean sliver_pub_ipv4 and _range
        if self.sliver_pub_ipv4 == 'none':
            if not self.sliver_pub_ipv4_range:
                # make sure empty sliver_pub_ipv4_range is None
                self.sliver_pub_ipv4_range = None
            else:
                raise ValidationError("If Sliver Public IPv4 is 'none' then Sliver "
                                      "Public IPv4 Range must be empty")
        elif self.sliver_pub_ipv4 == 'dhcp':
            validate_dhcp_range(self.sliver_pub_ipv4_range)
        elif self.sliver_pub_ipv4 == 'range':
            validate_ipv4_range(self.sliver_pub_ipv4_range)
        
        if not self.cert == '':
            # Empty cert as None instead of empty string (uniqueness)
            self.cert = None
        super(Node, self).clean()
    
    def update_set_state(self, commit=True):
        if not self.cert:
            # bad_conf
            self.set_state = Node.DEBUG
        else:
            if self.set_state == Node.DEBUG:
                # transition to safe when all config is correct
                self.set_state = Node.SAFE
            elif self.set_state == Node.PRODUCTION:
                #TODO transition to SAFE if changes are detected
                #     self.set_state = Node.SAFE
                pass
        if commit:
            self.save()
    
    def save(self, *args, **kwargs):
        self.update_set_state(commit=False)
        super(Node, self).save(*args, **kwargs)
    
    @property
    def mgmt_net(self):
        return get_mgmt_backend(self)
    
    def reboot(self):
        self.boot_sn += 1
        self.save()
    
    def get_sliver_mac_prefix(self):
        if self.sliver_mac_prefix: 
            return self.sliver_mac_prefix
        return settings.NODES_SLIVER_MAC_PREFIX_DFLT
    
    def get_priv_ipv4_prefix(self):
        if self.priv_ipv4_prefix:
            return self.priv_ipv4_prefix
        return settings.NODES_PRIV_IPV4_PREFIX_DFLT
    
    def get_priv_ipv6_prefix(self):
        return settings.NODES_PRIV_IPV6_PREFIX
    
    @property
    def sliver_pub_ipv4_num(self):
        """
        Number of available IPv4 for slivers
        
        [BASE_IP]#N when sliver_pub_ipv4_range is not empty
        """
        if self.sliver_pub_ipv4_range:
            return int(self.sliver_pub_ipv4_range.split('#')[1])
        return 0
    
    def sign_cert_request(self, scr, commit=True):
        self.cert = ssl.sign_cert_request(scr)
        if commit:
            self.save()
        return self.cert
    
    def generate_certificate(self, key, commit=False, user=None):
        if user is None:
            # We pick one pseudo-random admin
            user = self.group.admins[0]
        addr = str(self.mgmt_net.addr)
        self.cert = ssl.generate_certificate(key, Email=user.email, CN=addr)
        if commit:
            self.save()
        return self.cert
    
    def revoke_certificate(self):
        self.cert = None
        self.save()


class NodeProp(models.Model):
    """ 
    A mapping of (non-empty) arbitrary node property names to their (string) 
    values.
    """
    node = models.ForeignKey(Node, related_name='properties')
    name = models.CharField(max_length=32,
        help_text='Per node unique single line of free-form text with no '
                  'whitespace surrounding it.',
        validators=[validate_prop_name])
    value = models.CharField(max_length=256)
    
    class Meta:
        unique_together = ('node', 'name')
        verbose_name = 'Node Property'
        verbose_name_plural = 'Node Properties'
    
    def __unicode__(self):
        return self.name


class DirectIface(models.Model):
    """
    Interfaces used as direct interfaces.
    
    See node architecture: http://wiki.confine-project.eu/arch:node
    """
    name = models.CharField(max_length=16, validators=[validate_net_iface_name],
        help_text='he name of the interface used as a local interface (non-empty). '
                  'See <a href="https://wiki.confine-project.eu/arch:node">node '
                  'architecture</a>.')
    node = models.ForeignKey(Node, related_name='direct_ifaces')
    
    class Meta:
        unique_together = ['name', 'node']
        verbose_name = 'Direct Network Interface'
        verbose_name_plural = 'Direct Network Interfaces'
    
    def __unicode__(self):
        return self.name


class Server(SingletonModel):
    """
    Describes the testbed server (controller).
    """
    description = models.CharField(max_length=256,
        help_text='Free-form textual description of the server.')
    
    class Meta:
        verbose_name = "server"
        verbose_name_plural = "server"
    
    def __unicode__(self):
        return 'Server'
    
    def mgmt_net(self):
        return get_mgmt_backend(self)