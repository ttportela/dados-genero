python -u main.py ranchoalegredoeste --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/ranchoalegredoeste.txt
python -u main.py realeza --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/realeza.txt
python -u main.py reboucas --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/reboucas.txt
python -u main.py renascenca --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/renascenca.txt
