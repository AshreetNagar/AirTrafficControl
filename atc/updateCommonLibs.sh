

python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. data.proto
cp -rf . ../validator/
cp -rf . ../atc/
cp -rf . ../aircraft/