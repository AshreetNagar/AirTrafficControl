docker build -t aircraft .
# docker run --rm -d -p 8001:8001 --name aircraft aircraft
docker run --rm -p 8001:8001 --name aircraft aircraft
# docker logs atc_tower