python -u main.py tapira --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/tapira.txt
python -u main.py teixeirasoares --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/teixeirasoares.txt
python -u main.py telemacoborba --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/telemacoborba.txt
python -u main.py terraboa --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/terraboa.txt
