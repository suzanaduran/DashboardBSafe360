FROM python:3.9.6

RUN mkdir -p /root/.streamlit
RUN PYTHONPATH=$PYTHONPATH:$HOME

RUN bash -c 'echo -e "\
[general]\n\
email = \"\"\n\
" > /root/.streamlit/credentials.toml'

RUN bash -c 'echo -e "\
[server]\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
" > /root/.streamlit/config.toml'

EXPOSE $PORT

COPY dashboard_bsafe/requeriments.txt ./dasboard_bsafe/requeriments.txt
RUN pip3 install -r ./dashboard_bsafe/requeriments.txt
COPY dashboard_bsafe/ /dashboard_bsafe/

WORKDIR /dashboard_bsafe/

CMD streamlit run --server.port $PORT dashboard.py