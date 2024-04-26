docker build -t validatorserver .
docker run --rm -d -p 50051:50051 --name validatorserver validatorserver
# docker run --rm -p 50051:50051 --name validatorserver validatorserver
docker logs validatorserver