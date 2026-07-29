python -u main.py abatia --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/abatia.txt
python -u main.py adrianopolis --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/adrianopolis.txt
python -u main.py agudosdosul --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/agudosdosul.txt
python -u main.py almirantetamandare --sem-limite --etapa 1 --max-profundidade 10 --reprocessar-erros 2>&1 | tee -a resultados/_logs/almirantetamandare.txt
