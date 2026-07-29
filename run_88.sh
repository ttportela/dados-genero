python -u main.py serranopolisdoiguacu --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/serranopolisdoiguacu.txt
python -u main.py sertaneja --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/sertaneja.txt
python -u main.py sertanopolis --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/sertanopolis.txt
python -u main.py siqueiracampos --sem-limite --etapa 1 --max-profundidade 10 2>&1 | tee -a resultados/_logs/siqueiracampos.txt
