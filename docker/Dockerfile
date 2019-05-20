FROM merlin:latest
MAINTAINER Du.Wu allwu@falcon-computing.com
LABEL Version "0.1"

RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y python36u python36u-pip

RUN python3.6 -m pip install --trusted-host pypi.python.org setuptools future mypy pylint pytest \
    pytest-cov pytest-mock Sphinx sphinx_rtd_theme yapf tox argparse jsonpickle pickledb \
    redis texttable

RUN ln -s /usr/bin/python3.6 /usr/bin/python3

RUN yum install -y redis

COPY autodse /usr/local/bin
RUN chmod +x /usr/local/bin/autodse
COPY checkds /usr/local/bin
RUN chmod +x /usr/local/bin/checkds

COPY entrypoint.sh /usr/local/bin
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

ENV PYTHONPATH /opt/merlin_dse:${PYTHONPATH}
