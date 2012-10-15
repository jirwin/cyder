from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.shortcuts import render
from django.contrib import messages
from django.forms.util import ErrorList
from django.http import HttpResponse

from cyder.systems.models import System

from cyder.core.interface.static_intr.models import StaticInterface
from cyder.core.interface.static_intr.models import StaticIntrKeyValue
from cyder.core.interface.static_intr.forms import StaticInterfaceForm
from cyder.core.interface.static_intr.forms import FullStaticInterfaceForm
from cyder.core.interface.static_intr.forms import StaticInterfaceQuickForm
from cyder.core.interface.static_intr.forms import CombineForm
from cyder.core.keyvalue.utils import get_attrs, update_attrs, get_aa, get_docstrings
from cyder.core.keyvalue.utils import get_docstrings, dict_to_kv
from cyder.core.views import CoreDeleteView, CoreCreateView
from cyder.core.range.models import Range
from cyder.core.network.utils import calc_parent_str

from cyder.mozdns.domain.models import Domain
from cyder.mozdns.address_record.models import AddressRecord
from cyder.mozdns.ptr.models import PTR

import pdb
from cyder.core.search.parser import parse
from cyder.core.search.search import compile_search

import re
import ipaddr
import operator
import simplejson as json


from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('core.search', 'templates'))


def search_ajax(request):
    search = request.GET.get("search", None)
    if not search:
        return HttpResponse("What do you want?!?")
    dos_terms = ["10", "com", "mozilla.com", "mozilla", "network:10/8",
                 "network:10.0.0.0/8"]
    if search in dos_terms:
        return HttpResponse("Denial of Service attack prevented. The search "
                            "term '{0}' is to general".format(search))
    query = parse(search)
    print "----------------------"
    print query
    print "----------------------"

    x = compile_search(query)
    addrs, cnames, domains, intrs, mxs, nss, ptrs, srvs, txts, misc = x
    meta = {
        'counts': {
        'addr': addrs.count() if addrs else 0,
        'cname': cnames.count() if cnames else 0,
        'domain': domains.count() if domains else 0,
        'intr': intrs.count() if intrs else 0,
        'mx': mxs.count() if mxs else 0,
        'ns': nss.count() if nss else 0,
        'ptr': ptrs.count() if ptrs else 0,
        'txt': txts.count() if txts else 0,
        }
    }
    template = env.get_template('search/core_search_results.html')
    return HttpResponse(template.render(
        **{
        "misc": misc,
        "search": search,
        "addrs": addrs,
        "cnames": cnames,
        "domains": domains,
        "intrs": intrs,
        "mxs": mxs,
        "nss": nss,
        "ptrs": ptrs,
        "srvs": srvs,
        "txts": txts,
        "meta": meta,
        "search": search
        }
    ))


def search(request):
    """Search page"""
    search = request.GET.get('search', '')
    return render(request, "search/core_search.html", {
        "search": search
    })