# --------------------------------------------------------------------------- #
#                    ROBÔ DE SAÍDA  v3.0 PRO                                  #
#                          By-Rubemxz | Enhanced                              #
# --------------------------------------------------------------------------- #

import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
from ttkbootstrap import Style
from ttkbootstrap.constants import DEFAULT
import pyautogui
import time
import json
import os
import threading
import re
from typing import Dict, List, Tuple, Optional

# --- ARQUIVOS DE CONFIGURAÇÃO ---
ARQUIVO_ITENS = 'itens.txt'
ARQUIVO_COORDENADAS = 'coordenadas.json'

# --- VALORES PADRÃO ---
DEFAULTS = {
    'pyautogui_pause': 0.3,
    'tempo_espera_pesquisa': 4.0,
    'tempo_espera_confirmacao': 1.0
}

class ConfigManager:
    """Gerencia operações de leitura/escrita em arquivos de configuração."""
    
    def __init__(self, caminho_itens: str, caminho_coords: str):
        self.caminho_itens = caminho_itens
        self.caminho_coords = caminho_coords
    
    def carregar_itens(self) -> Dict[str, List[str]]:
        """Carrega itens organizados por categoria."""
        categorias = {'COZINHA': [], 'CARNES': []}
        categoria_atual = None
        
        try:
            with open(self.caminho_itens, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        categoria_atual = line[1:-1].upper()
                        if categoria_atual not in categorias:
                            categorias[categoria_atual] = []
                    elif categoria_atual:
                        categorias[categoria_atual].append(line)
            
            return categorias
        except (FileNotFoundError, IOError) as e:
            print(f"Erro ao carregar itens: {e}")
            return categorias
    
    def carregar_configuracoes(self) -> Tuple[Optional[Dict], Dict]:
        """Carrega coordenadas e configurações do arquivo JSON."""
        try:
            with open(self.caminho_coords, 'r') as f:
                data = json.load(f)
                coordenadas = data.get('coordenadas')
                configuracoes = data.get('configuracoes', DEFAULTS)
                return coordenadas, configuracoes
        except (FileNotFoundError, json.JSONDecodeError):
            return None, DEFAULTS
    
    def salvar_configuracoes(self, coords: Dict, configs: Dict) -> bool:
        """Salva coordenadas e configurações no arquivo JSON."""
        data = {'coordenadas': coords, 'configuracoes': configs}
        try:
            with open(self.caminho_coords, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except IOError as e:
            print(f"Erro ao salvar configurações: {e}")
            return False

class AutomationEngine:
    """Responsável pela execução das automações."""
    
    def __init__(self, coordenadas: Dict, configs: Dict):
        self.coordenadas = coordenadas
        self.configs = configs
        pyautogui.PAUSE = float(self.configs.get('pyautogui_pause', 0.3))
        pyautogui.FAILSAFE = True
    
    def _processar_item(self, item: str, quantidade: float, log_callback):
        """Processa um único item."""
        try:
            log_callback(f"📦 Processando: {item} | Qtd: {quantidade:.3f}")
            
            # Campo de busca
            pyautogui.click(self.coordenadas['busca']['x'], self.coordenadas['busca']['y'])
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
            pyautogui.write(item)
            pyautogui.press('enter')
            time.sleep(float(self.configs.get('tempo_espera_pesquisa', 4.0)))
            
            # Campo de quantidade
            pyautogui.click(self.coordenadas['quantidade']['x'], self.coordenadas['quantidade']['y'])
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
            pyautogui.write(str(quantidade).replace('.', ','))
            
            # Confirmação
            pyautogui.press('tab')
            time.sleep(float(self.configs.get('tempo_espera_confirmacao', 1.0)))
            pyautogui.press('enter')
            
            log_callback(f"✅ Item '{item}' processado com sucesso!")
        except Exception as e:
            log_callback(f"❌ ERRO ao processar '{item}': {e}")
            raise
    
    def run(self, itens: Dict[str, float], log_callback, progress_callback, stop_event, pause_event):
        """Executa a automação."""
        total_itens = len(itens)
        for i, (item, quantidade) in enumerate(itens.items()):
            if stop_event.is_set():
                log_callback("⚠️ Automação interrompida pelo usuário.")
                return "Interrompido"
            
            pause_event.wait()
            self._processar_item(item, quantidade, log_callback)
            progress_callback(i + 1, total_itens)
        
        return "✅ Processamento concluído com sucesso!"

class RaffinatoGUI:
    """Interface gráfica principal."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self._configurar_janela()
        self._inicializar_managers_e_eventos()
        self._construir_interface()
        self._atualizar_estado_botoes("ocioso")
    
    def _configurar_janela(self):
        self.root.title("🚀 Robô de Saídas v3.0 PRO - By-Rubemxz")
        self.root.geometry("1100x800")
        self.root.minsize(1000, 700)
    
    def _inicializar_managers_e_eventos(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_manager = ConfigManager(
            os.path.join(script_dir, ARQUIVO_ITENS),
            os.path.join(script_dir, ARQUIVO_COORDENADAS)
        )
        self.coordenadas, self.configs = self.config_manager.carregar_configuracoes()
        self.entradas: Dict[str, ttk.Entry] = {}
        self.widgets_itens: List[Dict] = []
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.categoria_selecionada = tk.StringVar(value="COZINHA")
    
    def _construir_interface(self):
        self.main_frame = ttk.Frame(self.root, padding="15")
        self.main_frame.pack(fill="both", expand=True)
        
        self._criar_header()
        self._criar_seletor_categoria()
        self._criar_barra_pesquisa()
        self._criar_lista_itens()
        self._criar_area_log()
        self._criar_area_progresso()
        self._criar_botoes_controle()
    
    def _criar_header(self):
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill="x", pady=(0, 15))
        
        titulo = ttk.Label(
            header_frame,
            text="🚀 Robô de Saídas v3.0 PRO",
            font=("Segoe UI", 22, "bold"),
            bootstyle="primary"
        )
        titulo.pack()
        
        subtitulo = ttk.Label(
            header_frame,
            text="Sistema Inteligente de Automação de Saídas",
            font=("Segoe UI", 10),
            bootstyle="secondary"
        )
        subtitulo.pack()
    
    def _criar_seletor_categoria(self):
        cat_frame = ttk.Labelframe(
            self.main_frame,
            text=" 📂 Selecione a Categoria ",
            padding="15",
            bootstyle="info"
        )
        cat_frame.pack(fill="x", pady=(0, 10))
        
        btn_frame = ttk.Frame(cat_frame)
        btn_frame.pack()
        
        ttk.Radiobutton(
            btn_frame,
            text="🍳 COZINHA",
            variable=self.categoria_selecionada,
            value="COZINHA",
            command=self._trocar_categoria,
            bootstyle="info-toolbutton",
            width=20
        ).pack(side="left", padx=5)
        
        ttk.Radiobutton(
            btn_frame,
            text="🥩 CARNES",
            variable=self.categoria_selecionada,
            value="CARNES",
            command=self._trocar_categoria,
            bootstyle="danger-toolbutton",
            width=20
        ).pack(side="left", padx=5)
    
    def _criar_barra_pesquisa(self):
        frame_pesquisa = ttk.Frame(self.main_frame)
        frame_pesquisa.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            frame_pesquisa,
            text="🔍 Pesquisar Item:",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filtrar_itens)
        search_entry = ttk.Entry(frame_pesquisa, textvariable=self.search_var, font=("Segoe UI", 10))
        search_entry.pack(side="left", fill="x", expand=True)
    
    def _criar_lista_itens(self):
        self.container_itens = ttk.Labelframe(
            self.main_frame,
            text=" 📋 Itens para Saída ",
            padding="10",
            bootstyle="primary"
        )
        self.container_itens.pack(fill="both", expand=True, pady=(0, 10))
        
        self.canvas_itens = tk.Canvas(self.container_itens, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.container_itens, orient="vertical", command=self.canvas_itens.yview)
        self.frame_itens = ttk.Frame(self.canvas_itens)
        
        self.frame_itens.bind("<Configure>", lambda e: self.canvas_itens.configure(scrollregion=self.canvas_itens.bbox("all")))
        self.canvas_itens.bind("<MouseWheel>", self._on_mousewheel)
        
        self.canvas_itens.create_window((0, 0), window=self.frame_itens, anchor="nw")
        self.canvas_itens.configure(yscrollcommand=scrollbar.set)
        self.canvas_itens.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self._carregar_itens_na_interface()
    
    def _carregar_itens_na_interface(self):
        self.itens_por_categoria = self.config_manager.carregar_itens()
        self._atualizar_lista_categoria()
    
    def _atualizar_lista_categoria(self):
        # Limpar widgets existentes
        for widget in self.frame_itens.winfo_children():
            widget.destroy()
        
        self.entradas.clear()
        self.widgets_itens.clear()
        
        categoria = self.categoria_selecionada.get()
        itens = self.itens_por_categoria.get(categoria, [])
        
        if not itens:
            ttk.Label(
                self.frame_itens,
                text=f"Nenhum item encontrado na categoria {categoria}",
                bootstyle="warning",
                font=("Segoe UI", 11)
            ).pack(pady=20)
            return
        
        # Criar header da tabela
        header_frame = ttk.Frame(self.frame_itens)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="ITEM",
            font=("Segoe UI", 10, "bold"),
            bootstyle="inverse-primary"
        ).grid(row=0, column=0, padx=10, sticky="w")
        
        if categoria == "CARNES":
            ttk.Label(
                header_frame,
                text="QUANTIDADE (use + para somar, ex: 25.5+12.6)",
                font=("Segoe UI", 10, "bold"),
                bootstyle="inverse-danger"
            ).grid(row=0, column=1, padx=10, sticky="w")
        else:
            ttk.Label(
                header_frame,
                text="QUANTIDADE",
                font=("Segoe UI", 10, "bold"),
                bootstyle="inverse-info"
            ).grid(row=0, column=1, padx=10, sticky="w")
        
        # Criar linhas de itens
        for idx, item in enumerate(itens, start=1):
            frame_item = ttk.Frame(self.frame_itens)
            frame_item.grid(row=idx, column=0, columnspan=2, sticky="ew", pady=2)
            
            label = ttk.Label(
                frame_item,
                text=item,
                font=("Segoe UI", 10),
                width=60
            )
            label.grid(row=0, column=0, padx=10, pady=6, sticky="w")
            
            entry = ttk.Entry(frame_item, width=30, font=("Segoe UI", 10))
            entry.insert(0, "0")
            entry.grid(row=0, column=1, padx=10, pady=6, sticky="ew")
            
            # Bind eventos de scroll
            label.bind("<MouseWheel>", self._on_mousewheel)
            entry.bind("<MouseWheel>", self._on_mousewheel)
            
            self.entradas[item] = entry
            self.widgets_itens.append({
                'frame': frame_item,
                'label': label,
                'entry': entry,
                'item_name': item.lower()
            })
    
    def _trocar_categoria(self):
        self._atualizar_lista_categoria()
        self.search_var.set("")
    
    def _filtrar_itens(self, *args):
        termo_busca = self.search_var.get().lower()
        for widget_info in self.widgets_itens:
            if termo_busca in widget_info['item_name']:
                widget_info['frame'].grid()
            else:
                widget_info['frame'].grid_remove()
    
    def _on_mousewheel(self, event):
        self.canvas_itens.yview_scroll(-1 * int(event.delta / 120), "units")
    
    def _criar_area_log(self):
        log_frame = ttk.Labelframe(
            self.main_frame,
            text=" 📄 Log de Execução ",
            padding="10",
            bootstyle="secondary"
        )
        log_frame.pack(fill="x", pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill="both", expand=True)
    
    def _criar_area_progresso(self):
        prog_frame = ttk.Frame(self.main_frame)
        prog_frame.pack(fill="x", pady=(0, 10))
        
        self.progressbar = ttk.Progressbar(prog_frame, mode='determinate', bootstyle="success-striped")
        self.progressbar.pack(fill="x")
    
    def _criar_botoes_controle(self):
        botoes_frame = ttk.Frame(self.main_frame)
        botoes_frame.pack(fill="x")
        
        self.btn_iniciar = ttk.Button(
            botoes_frame,
            text="▶ INICIAR AUTOMAÇÃO",
            command=self._iniciar_automacao,
            bootstyle="success",
            width=25
        )
        self.btn_iniciar.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.btn_pausar = ttk.Button(
            botoes_frame,
            text="⏸ PAUSAR",
            command=self._pausar_retomar_automacao,
            bootstyle="warning",
            width=20
        )
        self.btn_pausar.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_parar = ttk.Button(
            botoes_frame,
            text="⏹ PARAR",
            command=self._parar_automacao,
            bootstyle="danger",
            width=20
        )
        self.btn_parar.grid(row=0, column=2, padx=5, sticky="ew")
        
        self.btn_limpar = ttk.Button(
            botoes_frame,
            text="🧹 LIMPAR CAMPOS",
            command=self._limpar_campos,
            bootstyle="secondary",
            width=20
        )
        self.btn_limpar.grid(row=0, column=3, padx=5, sticky="ew")
        
        for i in range(4):
            botoes_frame.columnconfigure(i, weight=1)
    
    def _adicionar_log(self, mensagem: str):
        if self.root.winfo_exists():
            timestamp = time.strftime('%H:%M:%S')
            self.log_text.insert(tk.END, f"[{timestamp}] {mensagem}\n")
            self.log_text.see(tk.END)
            self.root.update_idletasks()
    
    def _atualizar_progresso(self, valor, total):
        if self.root.winfo_exists():
            self.progressbar['value'] = valor
            self.progressbar['maximum'] = total
            self.root.update_idletasks()
    
    def _limpar_campos(self):
        for entry in self.entradas.values():
            entry.delete(0, tk.END)
            entry.insert(0, "0")
        self._adicionar_log("🧹 Campos de quantidade foram limpos.")
    
    def _calcular_soma(self, expressao: str) -> float:
        """Calcula soma de expressões matemáticas (ex: 25.5+12.6)."""
        try:
            # Substituir vírgulas por pontos
            expressao = expressao.replace(',', '.')
            # Avaliar expressão matemática simples
            resultado = eval(expressao, {"__builtins__": {}}, {})
            return float(resultado)
        except:
            return 0.0
    
    def _obter_itens_selecionados(self) -> Dict[str, float]:
        """Obtém itens com quantidade > 0."""
        itens_processados = {}
        categoria = self.categoria_selecionada.get()
        
        for item, entry in self.entradas.items():
            valor_str = entry.get().strip()
            
            if not valor_str or valor_str == "0":
                continue
            
            # Para categoria CARNES, calcular soma se houver operação
            if categoria == "CARNES" and ('+' in valor_str or '-' in valor_str or '*' in valor_str or '/' in valor_str):
                quantidade = self._calcular_soma(valor_str)
                if quantidade > 0:
                    itens_processados[item] = quantidade
                    self._adicionar_log(f"🧮 {item}: {valor_str} = {quantidade:.3f}")
            else:
                try:
                    quantidade = float(valor_str.replace(',', '.'))
                    if quantidade > 0:
                        itens_processados[item] = quantidade
                except ValueError:
                    self._adicionar_log(f"⚠️ Valor inválido para '{item}': {valor_str}")
        
        return itens_processados
    
    def _atualizar_estado_botoes(self, estado: str):
        if estado == "ocioso":
            self.btn_iniciar.config(state="normal")
            self.btn_pausar.config(state="disabled", text="⏸ PAUSAR")
            self.btn_parar.config(state="disabled")
            self.btn_limpar.config(state="normal")
        elif estado == "executando":
            self.btn_iniciar.config(state="disabled")
            self.btn_pausar.config(state="normal", text="⏸ PAUSAR")
            self.btn_parar.config(state="normal")
            self.btn_limpar.config(state="disabled")
        elif estado == "pausado":
            self.btn_iniciar.config(state="disabled")
            self.btn_pausar.config(state="normal", text="▶ RETOMAR")
            self.btn_parar.config(state="normal")
            self.btn_limpar.config(state="disabled")
    
    def _pausar_retomar_automacao(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self._adicionar_log("⏸ Automação PAUSADA.")
            self._atualizar_estado_botoes("pausado")
        else:
            self.pause_event.set()
            self._adicionar_log("▶ Automação RETOMADA.")
            self._atualizar_estado_botoes("executando")
    
    def _parar_automacao(self):
        if messagebox.askyesno("Parar Automação", "⚠️ Tem certeza que deseja parar a execução?"):
            self.stop_event.set()
            if not self.pause_event.is_set():
                self.pause_event.set()
            self._adicionar_log("🛑 Parada solicitada pelo usuário...")
    
    def _calibrar_gps(self):
        self.root.iconify()
        try:
            messagebox.showinfo(
                "🎯 Calibração Necessária",
                "Vamos calibrar as posições do mouse.\n\n"
                "Pressione OK e siga as instruções no console."
            )
            
            print("\n" + "="*60)
            print("CALIBRAÇÃO - PASSO 1")
            print("="*60)
            input("Posicione o mouse sobre o CAMPO DE BUSCA e pressione Enter...")
            busca_pos = pyautogui.position()
            print(f"✅ Coordenada registrada: X={busca_pos.x}, Y={busca_pos.y}\n")
            
            messagebox.showinfo(
                "🎯 Calibração - Passo 2",
                "Agora, no sistema Raffinato, pesquise um item qualquer\n"
                "para que a janela de ajuste de quantidade apareça.\n\n"
                "Pressione OK quando estiver pronto."
            )
            
            print("="*60)
            print("CALIBRAÇÃO - PASSO 2")
            print("="*60)
            input("Posicione o mouse sobre o CAMPO DE QUANTIDADE e pressione Enter...")
            quantidade_pos = pyautogui.position()
            print(f"✅ Coordenada registrada: X={quantidade_pos.x}, Y={quantidade_pos.y}\n")
            
            self.coordenadas = {
                'busca': {'x': busca_pos.x, 'y': busca_pos.y},
                'quantidade': {'x': quantidade_pos.x, 'y': quantidade_pos.y}
            }
            
            if self.config_manager.salvar_configuracoes(self.coordenadas, self.configs):
                messagebox.showinfo("✅ Sucesso", "Calibração concluída com sucesso!")
                self._adicionar_log("✅ Calibração GPS concluída com sucesso!")
            else:
                messagebox.showerror("❌ Erro", "Não foi possível salvar as coordenadas.")
        finally:
            self.root.deiconify()
    
    def _iniciar_automacao(self):
        if not self.coordenadas:
            self._calibrar_gps()
            if not self.coordenadas:
                self._adicionar_log("❌ Calibração cancelada. Automaçãonão iniciada.")
                return
        
        itens_a_processar = self._obter_itens_selecionados()
        if not itens_a_processar:
            messagebox.showwarning("⚠️ Aviso", "Nenhum item com quantidade foi selecionado.")
            return
        
        self.stop_event.clear()
        self.pause_event.set()
        self._atualizar_progresso(0, len(itens_a_processar))
        self._atualizar_estado_botoes("executando")
        
        self._adicionar_log(f"🚀 Iniciando automação com {len(itens_a_processar)} item(ns)...")
        self._adicionar_log(f"📂 Categoria: {self.categoria_selecionada.get()}")
        
        threading.Thread(
            target=self._thread_executar_automacao,
            args=(itens_a_processar,),
            daemon=True
        ).start()
    
    def _thread_executar_automacao(self, itens: Dict[str, float]):
        try:
            self._adicionar_log("⏳ Aguardando 5 segundos para você posicionar a janela do Raffinato...")
            self.root.iconify()
            time.sleep(5)
            
            engine = AutomationEngine(self.coordenadas, self.configs)
            resultado = engine.run(
                itens,
                self._adicionar_log,
                self._atualizar_progresso,
                self.stop_event,
                self.pause_event
            )
            
            messagebox.showinfo("🎉 Concluído", resultado)
            self._adicionar_log(resultado)
            
        except Exception as e:
            self._adicionar_log(f"❌ ERRO CRÍTICO: {e}")
            messagebox.showerror("❌ Erro Crítico", f"Ocorreu um erro inesperado:\n\n{e}")
        finally:
            if self.root.winfo_exists():
                self.root.deiconify()
                self._atualizar_estado_botoes("ocioso")
                self._adicionar_log("✅ Pronto para nova execução.")

def main():
    """Função principal da aplicação."""
    root = tk.Tk()
    Style(theme='darkly')  # Tema moderno e profissional
    RaffinatoGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()