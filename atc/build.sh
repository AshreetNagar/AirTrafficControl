docker build -t atc_tower .
docker run --rm -d -p 8000:8000 --name atc_tower atc_tower
# docker run --rm -p 8000:8000 --name atc_tower atc_tower
# docker logs atc_tower