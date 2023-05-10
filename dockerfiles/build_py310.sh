set -ex
script_dir=$(cd "$(dirname "$0")" && pwd)
docker build -t py310 ${script_dir}/.. -f ${script_dir}/Dockerfile.py310
