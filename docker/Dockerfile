FROM merlin:latest
MAINTAINER Cody.Hao.Yu cody@falcon-computing.com
LABEL Version "0.1"

RUN python3.6 -m pip install --trusted-host pypi.python.org setuptools future mypy pylint pytest \
    pytest-cov pytest-mock Sphinx sphinx_rtd_theme yapf tox argparse jsonpickle pickledb \
    redis texttable

RUN yum install -y redis

COPY ./docker/autodse /usr/local/bin
RUN chmod +x /usr/local/bin/autodse
COPY ./docker/checkds /usr/local/bin
RUN chmod +x /usr/local/bin/checkds

COPY ./docker/entrypoint.sh /usr/local/bin
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

ADD . /opt/merlin_dse
ENV PYTHONPATH /opt/merlin_dse:${PYTHONPATH}
