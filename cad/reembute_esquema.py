# -*- coding: utf-8 -*-
"""Reembute imagens/esquema_eletrico.png (base64) dentro de Circuito_Braco_Robotico.html.

O guia de ligações carrega o esquema elétrico embutido, para o arquivo .html ser um só e abrir em
qualquer máquina sem a pasta imagens/. Por isso, depois de rodar cad/gerar_esquema.py é PRECISO
rodar este script, senão o guia continua mostrando o esquema antigo.

    python cad/gerar_esquema.py
    python cad/reembute_esquema.py
"""
import base64, io, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG  = os.path.join(RAIZ, "imagens", "esquema_eletrico.png")
HTML = os.path.join(RAIZ, "Circuito_Braco_Robotico.html")

with open(PNG, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")

with io.open(HTML, encoding="utf-8") as f:
    t = f.read()

PADRAO = re.compile(r'(<img class="esq"[^>]*?src="data:image/png;base64,)([A-Za-z0-9+/=]+)(")')
casos = PADRAO.findall(t)
if len(casos) != 1:
    sys.exit("ERRO: achei %d tag(s) <img class=\"esq\"> com PNG embutido (esperava 1)" % len(casos))

antigo = casos[0][1]
t = PADRAO.sub(lambda m: m.group(1) + b64 + m.group(3), t, count=1)

with io.open(HTML, "w", encoding="utf-8", newline="") as f:
    f.write(t)

print("ok: base64 trocado (%d -> %d caracteres, PNG de %d bytes)"
      % (len(antigo), len(b64), os.path.getsize(PNG)))
