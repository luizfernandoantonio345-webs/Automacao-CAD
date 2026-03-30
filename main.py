import os
import ezdxf
from api_isometrico import gerar_isometrico_dxf
from relatorio_generator import gerar_relatorio
from datetime import datetime

INPUT_DIR = "data/input"
OUTPUT_DIR = "data/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def main():
    print("🚀 Automação CAD Iniciada!")
    
    dados_projeto = {
        'projeto': 'TESTE_API_ISOMETRICO',
        'tubos': [{'id':1, 'diametro': '4\"', 'comprimento': 10}, {'id':2, 'diametro': '6\"', 'comprimento': 15}],
        'data': datetime.now().strftime('%Y-%m-%d')
    }
    
    dxf_path = os.path.join(OUTPUT_DIR, f"test_api_isometrico_{datetime.now().strftime('%Y%m%d')}.dxf")
    gerar_isometrico_dxf(dados_projeto, dxf_path)
    print(f"✅ DXF gerado: {dxf_path}")
    
    html_path = os.path.join(OUTPUT_DIR, f"test_api_relatorio_{datetime.now().strftime('%Y%m%d')}.html")
    md_path = os.path.join(OUTPUT_DIR, f"test_api_relatorio_{datetime.now().strftime('%Y%m%d')}.md")
    gerar_relatorio(dados_projeto, html_path, md_path)
    print(f"✅ Relatórios gerados.")
    
    print("🎉 Completo! Abra DXF no CAD.")

if __name__ == "__main__":
    main()

