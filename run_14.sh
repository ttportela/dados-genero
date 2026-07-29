python -u main.py cambira --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/cambira.txt
python -u main.py campinadalagoa --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/campinadalagoa.txt
python -u main.py campinadosimao --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/campinadosimao.txt
python -u main.py campinagrandedosul --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/campinagrandedosul.txt
