from django.urls import path
from . import views

urlpatterns = [
    path("", views.movies, name='movies'),
    path('<int:tmdb_id>/', views.movie_detail, name='movie_detail'),
    path("playlist/add/<int:tmdb_id>/", views.add_to_playlist, name="add_to_playlist"),
    path("playlist/", views.playlist_view, name="playlist"),
    path("playlist/remove/<int:item_id>/", views.remove_from_playlist, name="remove_from_playlist"),
    path('audio/', views.audio_player, name='audio_player'),
]
