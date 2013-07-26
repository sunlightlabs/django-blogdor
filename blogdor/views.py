import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic.dates import MonthArchiveView, YearArchiveView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from blogdor.models import Post
from tagging.models import Tag
from tagging.views import tagged_object_list

POSTS_PER_PAGE = getattr(settings, "BLOGDOR_POSTS_PER_PAGE", 10)
YEAR_POST_LIST = getattr(settings, "BLOGDOR_YEAR_POST_LIST", False)
WP_PERMALINKS = getattr(settings, "BLOGDOR_WP_PERMALINKS", False)

#
# Post detail views
#
                            
def post(request, year, slug):
    if WP_PERMALINKS:
        try:
            post = Post.objects.select_related().get(date_published__year=year, slug=slug)
            return HttpResponsePermanentRedirect(post.get_absolute_url())
        except Post.DoesNotExist:
            return HttpResponseRedirect(reverse('blogdor_archive'))
    else:
        return _post(request, year, slug)

def post_wpcompat(request, year, month, day, slug):
    if WP_PERMALINKS:
        return _post(request, year, slug)
    else:
        post = get_object_or_404(Post, date_published__year=year, slug=slug)
        return HttpResponsePermanentRedirect(post.get_absolute_url())

def _post(request, year, slug):
    try:
        return DetailView.as_view(model=Post,
                                  queryset=Post.objects.published().select_related().filter(date_published__year=year),
                                  slug=slug,
                                  context_object_name='post')
    except Http404, e:
        try:
            post = Post.objects.published().filter(date_published__year=year, slug__startswith=slug).latest('date_published')
            return HttpResponseRedirect(post.get_absolute_url())
        except Post.DoesNotExist:
            raise e

#
# Post archive views
#
                  
def archive(request):
    return ListView.as_view(model=Post,
                            queryset=Post.objects.published().select_related(),
                            paginate_by=POSTS_PER_PAGE,
                            context_object_name='post')

def archive_month(request, year, month):
    return MonthArchiveView.as_view(model=Post,
                                    queryset=Post.objects.published().select_related(),
                                    date_field='date_published',
                                    month=datetime.date(year, month, 1),
                                    context_object_name='post')

def archive_year(request, year):
    return YearArchiveView.as_view(model=Post,
                                   queryset=Post.objects.published().select_related(),
                                   date_field='date_published',
                                   year=year,
                                   context_object_name='post',
                                   make_object_list=YEAR_POST_LIST)

#
# Post tag views
#

def tag(request, tag):
    return tagged_object_list(
                    request,
                    Post.objects.published().select_related(),
                    tag,
                    paginate_by=POSTS_PER_PAGE,
                    template_object_name='post',
                    extra_context={'tag': tag},
                    allow_empty=True)

def tag_list(request):
    ct = ContentType.objects.get_for_model(Post)
    return ListView.as_view(model=Tag,
                            queryset=Tag.objects.filter(items__content_type=ct),
                            paginate_by=POSTS_PER_PAGE,
                            template_name='blogdor/tag_list.html',
                            context_object_name='tag')

#
# Author views
#

class AuthorListView(ListView):
    def get_context_data(self, **kwargs):
        context = super(AuthorListView, self).get_context_data(**kwargs)
        context.update({'author': self.author})
        return context

def author(request, username):
    try:
        author = User.objects.get(username=username)
        return AuthorListView.as_view(model=Post,
                                      author=author,
                                      queryset=Post.objects.published().select_related().filter(author=author),
                                      paginate_by=POSTS_PER_PAGE,
                                      context_object_name='post')
    except User.DoesNotExist:
        return HttpResponseRedirect(reverse('blogdor_archive'))

#
# Preview view
#

def preview(request, post_id, slug):
    try:
        post = Post.objects.select_related().get(pk=post_id, slug=slug)
        if post.is_published:
            return HttpResponsePermanentRedirect(post.get_absolute_url())
        else:
            return DetailView.as_view(model=Post,
                                      queryset=Post.objects.select_related().all(),
                                      object_id=post_id,
                                      context_object_name='post')
    except Post.DoesNotExist:
        return HttpResponseRedirect(reverse('blogdor_archive'))
