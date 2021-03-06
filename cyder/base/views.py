import simplejson as json

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse
from django.forms import ValidationError
from django.forms.util import ErrorList, ErrorDict
from django.db import IntegrityError
from django.shortcuts import (get_object_or_404, redirect, render,
                              render_to_response)
from django.views.generic import (CreateView, DeleteView, DetailView,
                                  ListView, UpdateView)

import cyder as cy
from cyder.base.utils import (_filter, do_sort, make_megafilter,
                              make_paginator, model_to_post, tablefy,
                              qd_to_py_dict)
from cyder.core.cyuser.utils import perm, perm_soft
from cyder.cydns.utils import ensure_label_domain


def home(request):
    return render_to_response('base/index.html', {
        'read_only': getattr(request, 'read_only', False),
    })


def cy_view(request, get_klasses_fn, template, pk=None, obj_type=None):
    """List, create, update view in one for a flatter heirarchy. """
    # Infer obj_type from URL, saves trouble of having to specify
    obj_type = obj_type or request.path.split('/')[2]

    Klass, FormKlass, FQDNFormKlass = get_klasses_fn(obj_type)
    obj = get_object_or_404(Klass, pk=pk) if pk else None
    form = FormKlass(instance=obj)

    if request.method == 'POST':
        form = FormKlass(request.POST, instance=obj)

        if form.is_valid():
            try:
                if perm(request, cy.ACTION_CREATE, obj=obj, obj_class=Klass):
                    obj = form.save()
                    return redirect(
                        request.META.get('HTTP_REFERER', obj.get_list_url()))
            except (ValidationError, ValueError) as e:
                if form._errors is None:
                    form._errors = ErrorDict()
                form._errors["__all__"] = ErrorList(e.messages)
                return render(request, template, {
                    'form': form,
                    'obj': obj,
                    'obj_type': obj_type,
                    'pk': pk,
                })
    elif request.method == 'GET':
        form = FormKlass(initial=qd_to_py_dict(request.GET))

    object_list = _filter(request, Klass)
    page_obj = make_paginator(request, do_sort(request, object_list), 50)

    return render(request, template, {
        'form': form,
        'obj': obj,
        'page_obj': page_obj,
        'object_table': tablefy(page_obj),
        'obj_type': obj_type,
        'pk': pk,
    })


def cy_delete(request, pk, get_klasses_fn):
    """DELETE. DELETE. DELETE."""
    obj_type = request.path.split('/')[2]
    Klass, FormKlass, FQDNFormKlass = get_klasses_fn(obj_type)
    obj = get_object_or_404(Klass, pk=pk)

    try:
        if perm(request, cy.ACTION_DELETE, obj=obj):
            obj.delete()
    except ValidationError as e:
        messages.error(request, ', '.join(e.messages))

    return redirect(request.META.get('HTTP_REFERER', obj.get_list_url()))


def cy_detail(request, Klass, template, obj_sets, pk=None, obj=None, **kwargs):
    """Show bunches of related tables.

    obj_sets -- string of foreign key attribute of the obj OR
                queryset relating to the obj

    Pass in either pk or already retrieved obj.
    """
    # Get object if needed.
    obj_type = request.path.split('/')[2]
    if not obj and pk:
        obj = get_object_or_404(Klass, pk=pk)
    elif not obj and pk:
        raise Exception("pk or obj required.")

    # Build related tables and paginators.
    tables = []
    for name, obj_set in obj_sets.items():
        if isinstance(obj_set, str):
            obj_set = getattr(obj, obj_set).all()
        page_obj = make_paginator(
            request, obj_set, obj_type=name.lower().replace(' ', ''))
        tables.append({
            'name': name,
            'page_obj': page_obj,
            'table': tablefy(page_obj)
        })

    return render(request, template, dict({
        'obj': obj,
        'obj_table': tablefy((obj,)),
        'obj_type': obj_type,
        'tables': tables
    }.items() + kwargs.items()))


def get_update_form(request, get_klasses_fn):
    """
    Update view called asynchronously from the list_create view
    """
    obj_type = request.GET.get('object_type', '')
    record_pk = request.GET.get('pk', '')
    related_type = request.GET.get('related_type', '')
    related_pk = request.GET.get('related_pk', '')
    kwargs = json.loads(request.GET.get('data', '{}').replace("'", "\""))
    if not obj_type:
        raise Http404

    Klass, FormKlass, FQDNFormKlass = get_klasses_fn(obj_type)

    try:
        # Get the object if updating.
        if record_pk:
            record = Klass.objects.get(pk=record_pk)
            if perm(request, cy.ACTION_UPDATE, obj=record):
                if FQDNFormKlass:
                    form = FQDNFormKlass(instance=record)
                else:
                    form = FormKlass(instance=record)
        else:
            #  Get form to create a new object and prepopulate
            if related_type and related_pk:
                form = FormKlass(initial=dict(
                    {related_type: related_pk}.items() + kwargs.items()))
            else:
                form = FormKlass(initial=kwargs)
    except ObjectDoesNotExist:
        raise Http404

    return HttpResponse(
        json.dumps({'form': form.as_p(), 'pk': record_pk or ''}))


def search_obj(request, get_klasses_fn):
    """
    Returns a list of objects of 'obj_type' matching 'term'.
    """
    obj_type = request.GET.get('obj_type', '')
    term = request.GET.get('term', '')
    if not (obj_type and term):
        raise Http404

    Klass, FormKlass, FQDNFormKlass = get_klasses_fn(obj_type)

    records = Klass.objects.filter(make_megafilter(Klass, term))[:15]
    records = [{'label': str(record), 'pk': record.pk} for record in records]

    return HttpResponse(json.dumps(records))


def table_update(request, pk, get_klasses_fn, object_type=None):
    """
    Called from editableGrid tables when updating a field. Try to update
    an object specified by pk with the post data.
    """
    # Infer object_type from URL, saves trouble of having to specify
    # kwargs everywhere in the dispatchers.
    object_type = object_type or request.path.split('/')[2]

    Klass, FormKlass, FQDNFormKlass = get_klasses_fn(object_type)
    obj = get_object_or_404(Klass, pk=pk)

    if not perm_soft(request, cy.ACTION_UPDATE, obj=obj):
        return HttpResponse(json.dumps({'error': 'You do not have appropriate'
                                                 ' permissions.'}))

    # DNS specific.
    qd = request.POST.copy()
    if 'fqdn' in qd:
        fqdn = qd.pop('fqdn')[0]
        try:
            # Call prune tree later if error, else domain leak.
            label, domain = ensure_label_domain(fqdn)
        except ValidationError, e:
            return HttpResponse(json.dumps({'error': e.messages}))
        qd['label'], qd['domain'] = label, str(domain.pk)

    form = FormKlass(model_to_post(qd, obj), instance=obj)
    if form.is_valid():
        form.save()
        return HttpResponse()
    return HttpResponse(json.dumps({'error': form.errors}))


class BaseListView(ListView):
    """
    Inherit ListView to specify our pagination.
    """
    template_name = 'list.html'
    extra_context = None
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = super(ListView, self).get_context_data(**kwargs)
        context['Model'] = self.model
        context['model_name'] = self.model._meta.db_table
        context['object_table'] = tablefy(context['page_obj'])
        context['form_title'] = "{0} Details".format(
            self.form_class.Meta.model.__name__
        )
        # Extra_context takes precedence over original values in context.
        try:
            context = dict(context.items() + self.extra_context.items())
        except AttributeError:
            pass
        return context


class BaseDetailView(DetailView):
    template_name = 'detail.html'
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context['form_title'] = "{0} Details".format(
            self.form_class.Meta.model.__name__
        )
        # Extra_context takes precedence over original values in context.
        try:
            context = dict(context.items() + self.extra_context.items())
        except AttributeError:
            pass
        return context


class BaseCreateView(CreateView):
    template_name = "form.html"
    extra_context = None

    def post(self, request, *args, **kwargs):
        try:
            obj = super(BaseCreateView, self).post(request, *args, **kwargs)
        # Redirect back to form if errors.
        except (IntegrityError, ValidationError), e:
            messages.error(request, str(e))
            request.method = 'GET'
            return super(BaseCreateView, self).get(request, *args, **kwargs)
        return obj

    def get(self, request, *args, **kwargs):
        return super(BaseCreateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)
        context['form_title'] = "Create {0}".format(
            self.form_class.Meta.model.__name__
        )
        # Extra_context takes precedence over original values in context.
        try:
            context = dict(context.items() + self.extra_context.items())
        except AttributeError:
            pass
        return context


class BaseUpdateView(UpdateView):
    template_name = "form.html"
    extra_context = None

    def __init__(self, *args, **kwargs):
        super(UpdateView, self).__init__(*args, **kwargs)

    def get_form(self, form_class):
        form = super(BaseUpdateView, self).get_form(form_class)
        return form

    def post(self, request, *args, **kwargs):
        try:
            obj = super(BaseUpdateView, self).post(request, *args, **kwargs)

        except ValidationError, e:
            messages.error(request, str(e))
            request.method = 'GET'
            return super(BaseUpdateView, self).get(request, *args, **kwargs)

        return obj

    def get(self, request, *args, **kwargs):
        return super(BaseUpdateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['form_title'] = "Update {0}".format(
            self.form_class.Meta.model.__name__
        )

        # Extra_context takes precedence over original values in context.
        try:
            context = dict(context.items() + self.extra_context.items())
        except AttributeError:
            pass

        return context


class BaseDeleteView(DeleteView):
    template_name = 'confirm_delete.html'
    extra_content = None
    success_url = '/'

    def get_object(self, queryset=None):
        obj = super(BaseDeleteView, self).get_object()
        return obj

    def delete(self, request, *args, **kwargs):
        # Get the object to delete.
        obj = get_object_or_404(self.form_class.Meta.model,
                                pk=kwargs.get('pk', 0))
        try:
            view = super(BaseDeleteView, self).delete(request, *args, **kwargs)
        except ValidationError, e:
            messages.error(request, "Error: {0}".format(' '.join(e.messages)))
            return redirect(obj)

        messages.success(request, "Deletion Successful")
        return view

    def get_context_data(self, **kwargs):
        context = super(DeleteView, self).get_context_data(**kwargs)
        context['form_title'] = "Update {0}".format(
            self.form_class.Meta.model.__name__
        )
        # Extra_context takes precedence over original values in context.
        try:
            context = dict(context.items() + self.extra_context.items())
        except AttributeError:
            pass
        return context


class Base(DetailView):
    def get(self, request, *args, **kwargs):
        return render(request, "base.html")
