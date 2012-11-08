from django.conf.urls.defaults import *
from django.views.decorators.csrf import csrf_exempt

from cyder.cydns.cname.views import *
from cyder.cydns.views import cydns_list_create_record

urlpatterns = patterns('',
   url(r'^$', cydns_list_create_record, name='cname-list'),

   url(r'(?P<domain>[\w-]+)/create/$',
       csrf_exempt(CNAMECreateView.as_view()), name='cname-create-in-domain'),

   url(r'(?P<pk>[\w-]+)/update/$',
       cydns_list_create_record, name='cname-update'),
   url(r'(?P<pk>[\w-]+)/delete/$',
       csrf_exempt(CNAMEDeleteView.as_view()), name='cname-delete'),
   url(r'(?P<pk>[\w-]+)/$',
       csrf_exempt(CNAMEDetailView.as_view()), name='cname-detail'),
)