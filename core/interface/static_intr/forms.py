from django import forms
from django.forms import models
from django.core.exceptions import ValidationError

from core.interface.static_intr.models import StaticInterface
from mozdns.domain.models import Domain
from mozdns.validation import validate_label
from core.vlan.models import Vlan
from core.site.models import Site
#from mozdns.mozdhcp.validation import validate_mac

import ipaddr
import pdb

def validate_ip(ip):
    try:
        ipaddr.IPv4Address(ip)
    except ipaddr.AddressValueError, e:
        try:
            ipaddr.IPv6Address(ip)
        except ipaddr.AddressValueError, e:
            raise ValidationError("IP address not in valid form.")

class StaticInterfaceForm(forms.Form):
    #mac = forms.CharField(validators=[validate_mac])
    hostname = forms.CharField(validators=[validate_label])
    domain = forms.ModelChoiceField(queryset=Domain.objects.all())
    ip = forms.CharField(validators=[validate_ip])
    IP_TYPE = (('4', 'IPv4'), ('6', 'IPv6'))
    ip_type = forms.ChoiceField(choices=IP_TYPE)

class StaticInterfaceQuickForm(forms.Form):
    #mac = forms.CharField(validators=[validate_mac])
    hostname = forms.CharField(validators=[validate_label])
    IP_TYPE = (('4', 'IPv4'), ('6', 'IPv6'))
    ip_type = forms.ChoiceField(choices=IP_TYPE)
    vlan = forms.ModelChoiceField(queryset=Vlan.objects.all())
    site = forms.ModelChoiceField(queryset=Site.objects.all())