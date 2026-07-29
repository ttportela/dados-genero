python -u main.py porecatu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/porecatu.txt
python -u main.py portoamazonas --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/portoamazonas.txt
python -u main.py portobarreiro --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/portobarreiro.txt
python -u main.py portorico --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/portorico.txt
