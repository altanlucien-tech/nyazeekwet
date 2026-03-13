from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.welcome_page, name='welcome'),
    
    # Library & Shop
    path('library/', views.library_view, name='library'),
    path('shop/', views.shop_view, name='shop'),

    # Manga APIs
    path('manga-chapters/<int:manga_id>/', views.manga_chapters_api, name='manga_chapters_api'),
    path('manga/chapter/<int:chapter_id>/', views.read_chapter, name='read_chapter'),

    # Ads & Progress
    path('show-ads/', views.show_ads_before_read, name='show_ads'),
    path('update-pdf-page/', views.update_pdf_page, name='update_pdf_page'),
    path('update-audio-position/', views.update_audio_position, name='update_audio_position'),
    
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='library'), name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Actions
    path('read/<int:book_id>/', views.read_book, name='read_book'),
    path('listen/<int:book_id>/', views.listen_book, name='listen_book'),
    path('audio-stream/<int:book_id>/', views.audio_stream, name='audio_stream'),
    path('payment/', views.payment_page, name='payment'),
    path('search-suggestions/', views.book_search_suggestions, name='search_suggestions'),
    path('books/', views.book_list_view, name='book_list'),
]