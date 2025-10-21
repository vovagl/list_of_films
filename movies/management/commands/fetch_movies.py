import requests
from django.core.management.base import BaseCommand
from movies.models import Movie

API_KEY = "569a626449cb32e3f1ff7230420b1dce"
BASE_URL = "https://api.themoviedb.org/3/movie/popular"
LANG = "ru-RU"   # можно "en-US"

class Command(BaseCommand):
    help = "Fetch all popular movies (500 pages) from TMDB and save to database"

    def handle(self, *args, **kwargs):
        total_new = 0
        total_updated = 0

        for page in range(1, 501):  # 500 страниц
            url = f"{BASE_URL}?api_key={API_KEY}&language={LANG}&page={page}"
            response = requests.get(url)

            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(
                    f"Ошибка {response.status_code} на странице {page}"
                ))
                break

            data = response.json()
            results = data.get("results", [])

            for item in results:
                obj, created = Movie.objects.update_or_create(
                    tmdb_id=item["id"],
                    defaults={
                        "title": item.get("title"),
                        "release_date": item.get("release_date") or None,
                        "rating": item.get("vote_average"),
                        "poster_path": item.get("poster_path")
                    }
                )
                if created:
                    total_new += 1
                else:
                    total_updated += 1

            self.stdout.write(self.style.SUCCESS(
                f"✅ Страница {page}: {len(results)} фильмов обработано"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Импорт завершён ✅ Добавлено: {total_new}, обновлено: {total_updated}"
        ))
