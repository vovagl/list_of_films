from django.db import models


class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True)   # ID из TMDB
    title = models.CharField(max_length=255)
    release_date = models.DateField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)
    poster_path = models.CharField(max_length=255, null=True, blank=True)  # путь к постеру

    def __str__(self):
        return self.title

    @property
    def poster_url(self):
        if self.poster_path:
            path = self.poster_path
            if not path.startswith("/"):
                path = "/" + path
            return f"https://image.tmdb.org/t/p/w200{path}"
        return "https://via.placeholder.com/200x300?text=No+Image"

    @property
    def rating_percentage(self):
        if self.rating is None:
            return 0
        return (self.rating / 10) * 100
    
class Playlist(models.Model):
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Playlist ({self.session_key})" 
    
class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, related_name="items" , on_delete=models.CASCADE)
    tmdb_id = models.IntegerField()
    title = models.CharField(max_length=255)
    poster_url = models.CharField(max_length=500, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("playlist", "tmdb_id")

    def __str__(self):
        return f"{self.title} (TMDB {self.tmdb_id})"      