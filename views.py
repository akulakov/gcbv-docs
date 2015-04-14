from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

from django.contrib.auth import authenticate, login
from django.forms.formsets import formset_factory

from django import forms
from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse_lazy, reverse
from django.forms.models import inlineformset_factory, modelformset_factory
from django.views.generic import *
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.edit import FormMixin

from app1.models import *

"""
The following customized GCBV views are included below:

    - ContextFormMixin - FormMixin with added get_context_data().

    - AuthorDetail - combined DetailView and ListView.

    - AuthorDetail2 - combined DetailView and ContextFormView.

    - BooksFormView - combined ListView and ContextFormView.

    - NFormsView - class for processing arbitrary number of forms, accepting input from only one of them that
          user chose to submit. (inherits from FormView)

    - CreateUpdateBook - combined create / update view, inherits from UpdateView.

    - AuthorBooksView - combined SingleObjectMixin, MultipleObjectMixin, ContextFormView.

    - BooksCreateView - combined ListView and ContextCreateView.

    - CommentFormsetView - inherits from FormView, tweaked to process formset instead of form.

    - BookInlineFormsetView - inherits from FormView, tweaked to process inline formset instead of form.

    (Note: example for a modelformset view is not provided because it would be too "hacky" to adapt FormView
    to handle a modelformset. Instead it's recommended to use one of the available 3rd party implementations
    of ModelFormsetView).
"""


class ContextFormMixin(FormMixin):
    def get_context_data(self, **kwargs):
        """ Normally FormMixin uses get() to add form to context, but logically this should happen in
            get_context_data(), and this is consistent with Single- and Multiple- ObjectMixins and this also
            allows for better mixability.
        """
        context = dict(form=self.get_form())
        context.update(kwargs)
        return super(ContextFormMixin, self).get_context_data(**context)

class ContextFormView(ContextFormMixin, FormView):
    pass
class ContextUpdateView(ContextFormMixin, UpdateView):
    pass
class ContextCreateView(ContextFormMixin, CreateView):
    pass


class AuthorDetail(DetailView, ListView):
    """ Combined detail / list view.

        Note: here we're not using `allow_empty` functionality in ListView.get(), if we needed that, we would need to
        override get_queryset() method and use a `super()` call in get().
    """
    paginate_by = 2
    model = Author
    context_object_name = "author"
    template_name = "author.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object_list = self.object.books.all()
        return self.render_to_response(self.get_context_data())


class AuthorInterestForm(forms.Form):
    message = forms.CharField()

class CommentForm(forms.Form):
    comment = forms.CharField()


class AuthorDetail2(DetailView, ContextFormView):
    """ We're using DetailView.get() to set self.object and ContextFormView.post() for POST logic; and using
        get_context_data() from both.

        note: we need to set up self.object in post() for it to be used in form_valid() and form_invalid().

        note 2: if a form doesn't have error conditions, e.g. if all fields are optional charfields, you can
        omit the post() method and use get_object() directly in form_valid() because form_invalid() will never
        be used.
    """
    model = Author
    form_class = AuthorInterestForm
    template_name = "author2.html"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(AuthorDetail, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        # Here, we would have some logic based on user's form inputs
        print ("in form_valid()")
        return redirect('author', pk=self.object.pk)


class BooksFormView(ListView, ContextFormView):
    """ Mixing with ListView is almost the same as with DetailView.

        We're using ListView.get() to set self.object_list and ContextFormView.post() for POST logic; and using
        get_context_data() from both.

        note: we need to set up self.object_list in post() for it to be used in form_valid() and form_invalid().

        note 2: if a form doesn't have error conditions, e.g. if all fields are optional charfields, you can
        omit the post() method and use get_queryset() directly in form_valid() because form_invalid() will never
        be used.
    """
    model = Book
    form_class = AuthorInterestForm
    paginate_by = 2
    template_name = "books.html"

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        return super(BooksFormView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        # Here, we would have some logic based on user's form inputs
        print ("in form_valid()")
        return redirect('books-form')


class NFormsView(FormView):
    """ Arbitrary number of  forms are shown on a page but only one is submitted at a time, tracked by submit
        button's `name` attr.

        get(), post() and form_valid() are updated in a straightforward way to handle N forms
        mapped by names instead of a single form.

        form_invalid() is more complex: we need to insert the bound form instance being handled, the one we get
        from post(), along with its errors; we also need to instantiate the other forms without using
        `get_form()` because `get_form()` creates a bound form instance on POST requests.
    """
    form_classes = dict(
                        comment_form = CommentForm,
                        author_form = AuthorInterestForm,
                        )
    template_name = "two-forms.html"

    def get(self, request, *args, **kwargs):
        context = {n: cls() for n, cls in self.form_classes.items()}
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        for name, cls in self.form_classes.items():
            if name in request.POST:
                form = self.get_form(cls)
                break

        if form.is_valid():
            return self.form_valid(name, form)
        else:
            return self.form_invalid(name, form)

    def form_valid(self, name, form):
        # Here, we would have some logic based on user's form inputs
        print ("in form_valid()", name)
        return redirect('two-forms')

    def form_invalid(self, name, form):
        context = {n: cls() for n, cls in self.form_classes.items()}
        context.update({name: form})
        return self.render_to_response(context)


class CreateUpdateBook(UpdateView):
    """ Create-Update view: if self.object is set to None, ModelForm creates a new object.
    """
    model = Book
    fields = ["name", "author"]
    success_url = reverse_lazy("books-form")
    template_name = "update-book.html"

    def get_object(self):
        try:
            return super(CreateUpdateBook, self).get_object()
        except AttributeError:
            return None


class AuthorBooksView(SingleObjectMixin, MultipleObjectMixin, ContextFormView):
    """ We're overriding get() and post() methods to set up `self.object` and `self.object_list` which will
        be used in respective get_context_data() methods.

        An alternative would be to override get_context_data() where `self.object` and `self.object_list`
        would be set instead, and override post() where only `self.object` would need to be set because
        it is needed in form_valid() -- when form is valid, get_context_data() does not run because context
        is not needed.

        `SingleObjectMixin` is first in the inheritance list to make sure its get_context_data() method runs
        first and therefore its `context_object_name` value gets precedence. Alternatively we could reverse
        the order of inheritance, set `context_object_name` to 'books' and use `object` and `books` in the template.

        note: if a form doesn't have error conditions, e.g. if all fields are optional charfields, you can
        omit the post() method and use get_object() directly in form_valid() because form_invalid() will never
        be used.
    """
    model = Author
    form_class = AuthorInterestForm
    paginate_by = 2
    context_object_name = "author"
    template_name = "author-books.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object_list = self.object.books.all()
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object_list = self.object.books.all()
        return super(AuthorBooksView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        # Here, we would have some logic based on user's form inputs
        print ("in form_valid()")
        return redirect("author-books", pk=self.object.pk)


class BooksCreateView(ListView, ContextCreateView):
    """
        We're overriding get_context_data() to set up `self.object` and `self.object_list` to
        be used in respective parent get_context_data() methods.

        Note: we cannot rely on ListView.get() to create `self.object_list` because we also need it on POST,
        when form_invalid() calls get_context_data().
    """
    model         = Book
    paginate_by   = 10
    fields        = ["name", "author"]
    success_url   = reverse_lazy("list-books-create")
    template_name = "books.html"

    def get_context_data(self, **kwargs):
        self.object = None
        self.object_list = self.get_queryset()
        return super(BooksCreateView, self).get_context_data(**kwargs)


CommentFormSet = formset_factory(CommentForm, extra=5)

class CommentFormsetView(FormView):
    form_class    = CommentFormSet
    template_name = "comment-formset.html"

    def form_valid(self, formset):
        for form in formset:
            # do something with form
            pass
        return redirect("comment-formset")


InlineBookFormSet = inlineformset_factory(Author, Book, fields=('name',))

class BookInlineFormsetView(DetailView, ContextUpdateView):
    model = Author
    form_class = InlineBookFormSet
    template_name = "book-formset.html"

    def get_success_url(self):
        # note that we use self.get_object() because self.object at this point will be a list returned by
        # formset.save()
        return reverse("book-inline-formset", kwargs=dict(pk=self.get_object().pk))
