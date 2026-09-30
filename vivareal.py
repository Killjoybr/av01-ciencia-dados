import time
import random
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def limpar_texto(texto):
    if not texto:
        return None
    return re.sub(r'\s+', ' ', texto).strip()

def extrair_numero(texto):
    if not texto:
        return None
    numeros = re.findall(r'\d+', texto)
    return numeros[0] if numeros else None

def raspar_vivareal_edge(limite_imoveis=100):
    options = Options()
    options.add_argument("--window-size=1920,1080")
    
    # Estratégias Anti-Bloqueio (Evasão de Bot)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
    
    driver = webdriver.Edge(options=options)
    
    # Executa script CDP para remover a propriedade webdriver do navegador
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    todos_imoveis = []
    pagina = 1
    url_base = "https://www.vivareal.com.br/venda/distrito-federal/brasilia/bairros/sobradinho/"

    print(f"Iniciando captura no Edge até obter {limite_imoveis} imóveis...")

    try:
        # Acessa a página base APENAS UMA VEZ antes do loop
        driver.get(url_base)
        time.sleep(random.uniform(3.0, 5.0))

        while len(todos_imoveis) < limite_imoveis:
            print(f"\nExtraindo dados da página {pagina}...")

            # Fechar modal
            try:
                botao_fechar = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Fechar modal']"))
                )
                botao_fechar.click()
                print("Pop-up fechado com sucesso.")
                time.sleep(random.uniform(1.0, 2.0)) 
            except TimeoutException:
                pass

            # Aguarda os cards carregarem
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-cy="rp-property-cd"]'))
                )
            except TimeoutException:
                print("Tempo limite excedido aguardando os imóveis. Encerrando.")
                break

            # Scroll para simular leitura e carregar imagens/dados (lazy loading)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
            time.sleep(random.uniform(1.0, 2.0))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 1.5);")
            time.sleep(random.uniform(1.0, 2.0))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 3.0))

            cards = driver.find_elements(By.CSS_SELECTOR, '[data-cy="rp-property-cd"]')
            
            if not cards:
                print("Nenhum card encontrado nesta página.")
                break

            # Extração dos dados
            for card in cards:
                if len(todos_imoveis) >= limite_imoveis:
                    break
                
                imovel = {}
                
                try:
                    preco_elem = card.find_element(By.CSS_SELECTOR, 'span.typo-title-small.font-bold')
                    imovel['preco'] = limpar_texto(preco_elem.text)
                except NoSuchElementException:
                    imovel['preco'] = None
                
                try:
                    area_elem = card.find_element(By.CSS_SELECTOR, '[data-cy="rp-cardProperty-propertyArea-txt"]')
                    imovel['area_m2'] = extrair_numero(area_elem.text)
                except NoSuchElementException:
                    imovel['area_m2'] = None
                    
                try:
                    quartos_elem = card.find_element(By.CSS_SELECTOR, '[data-cy="rp-cardProperty-bedroomQuantity-txt"]')
                    imovel['quartos'] = extrair_numero(quartos_elem.text)
                except NoSuchElementException:
                    imovel['quartos'] = None
                    
                try:
                    banheiros_elem = card.find_element(By.CSS_SELECTOR, '[data-cy="rp-cardProperty-bathroomQuantity-txt"]')
                    imovel['banheiros'] = extrair_numero(banheiros_elem.text)
                except NoSuchElementException:
                    imovel['banheiros'] = None
                    
                try:
                    vagas_elem = card.find_element(By.CSS_SELECTOR, '[data-cy="rp-cardProperty-parkingSpacesQuantity-txt"]')
                    imovel['vagas'] = extrair_numero(vagas_elem.text)
                except NoSuchElementException:
                    imovel['vagas'] = None
                    
                try:
                    endereco_elem = card.find_element(By.CSS_SELECTOR, '[data-cy="rp-cardProperty-location-txt"]')
                    imovel['bairro'] = limpar_texto(endereco_elem.text)
                    endereco_elem = card.find_element(By.CSS_SELECTOR, '[data-cy="rp-cardProperty-street-txt"]')
                    imovel['bairro'] = imovel['bairro']+f' {limpar_texto(endereco_elem.text)}'
                except NoSuchElementException:
                    imovel['bairro'] = None

                try:
                    titulo_elem = card.find_element(By.CSS_SELECTOR, "h2.block.overflow-hidden.text-ellipsis.whitespace-nowrap.typo-caption.text-neutral-100")
                    titulo_texto = limpar_texto(titulo_elem.text).lower()
                    
                    if 'apartamento' in titulo_texto:
                        imovel['tipo'] = 'apartamento'
                    elif 'casa' in titulo_texto:
                        imovel['tipo'] = 'casa'
                    elif 'lote' in titulo_texto or 'terreno' in titulo_texto:
                        imovel['tipo'] = 'terreno'
                    elif 'chácara' in titulo_texto or 'sítio' in titulo_texto:
                        imovel['tipo'] = 'chacara'
                    else:
                        imovel['tipo'] = titulo_texto.split()[0] if titulo_texto else 'outro'
                except NoSuchElementException:
                    imovel['tipo'] = None

                todos_imoveis.append(imovel)
            
            print(f"Total acumulado: {len(todos_imoveis)} imóveis.")
            
            if len(todos_imoveis) >= limite_imoveis:
                break

            try:
                btn_proxima = driver.find_element(By.CSS_SELECTOR, "a[aria-label='próxima página']")
                
                if btn_proxima.get_attribute("aria-disabled") == "true":
                    print("Chegamos na última página disponível.")
                    break
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_proxima)
                time.sleep(random.uniform(0.5, 1.5))
                
                driver.execute_script("arguments[0].click();", btn_proxima)
                print("Navegando via clique no botão 'próxima página'...")
                
                pagina += 1
                
                time.sleep(random.uniform(4.0, 6.0))
                
            except NoSuchElementException:
                print("Botão de próxima página não encontrado no HTML. Fim da paginação.")
                break

    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        driver.quit()

    if todos_imoveis:
        df = pd.DataFrame(todos_imoveis)
        nome_arquivo = 'imoveis_sobradinho.csv'
        df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig')
        print(f"\nSucesso! {len(todos_imoveis)} imóveis salvos no arquivo '{nome_arquivo}'.")
    else:
        print("\nNenhum dado foi capturado.")

if __name__ == "__main__":
    raspar_vivareal_edge(limite_imoveis=100)