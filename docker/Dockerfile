FROM python:3.10-slim
RUN apt update && apt -y install ca-certificates software-properties-common curl gnupg2 gnupg-agent \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1001 hventure \
    && useradd -rm -d /home/hventure -s /bin/bash -g hventure -G sudo -u 1001 hventure \
    && mkdir /home/hventure/application /home/hventure/.aws && chown -Rv 1001:1001 /home/hventure/ && chmod 700 /home/hventure/.aws && ln -s /bin/python3 /bin/python
ENTRYPOINT ["/bin/bash"]

#    && add-apt-repository -y ppa:mozillateam/ppa \
#    && apt -y  install firefox \

#USER hventure
#RUN curl -sSL https://install.python-poetry.org | python3 -
#COPY --chown=1001:1001 *.py *.toml /home/hventure/application/
#RUN cd /home/hventure/application/ \
#    && python -m venv venv \
#    &&  . venv/bin/activate \
#    && $HOME/.local/bin/poetry install \
#    && deactivate
#USER root
#RUN apt -y remove curl software-properties-common gnupg2 gnupg-agent && apt -y autoremove
#USER hventure
#WORKDIR /home/hventure/application
#RUN echo "#!/usr/bin/env sh\nentrypoint_args=\$1\nidp=\$(echo \$entrypoint_args|cut -d':' -f1)\nusername=idp=\$(echo \$entrypoint_args|cut -d':' -f2)\n. venv/bin/activate\npython3 ./getCredentials.py --container --textmenu --idp \$idp --username \$username\n" >> entrypoint.sh
#RUN pwd && cat entrypoint.sh && chmod 755 entrypoint.sh
#ENTRYPOINT ["./entrypoint.sh"]
#
#

