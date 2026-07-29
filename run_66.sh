python -u main.py planaltinadoparana --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/planaltinadoparana.txt
python -u main.py planalto --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/planalto.txt
python -u main.py pontagrossa --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/pontagrossa.txt
python -u main.py pontaldoparana --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/pontaldoparana.txt
