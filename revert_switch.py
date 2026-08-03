import sys
content = open("rlm_optimized/tui_app.py", "r").read()

# Revert Switch and Static back to a Button
content = content.replace('yield Static("⚡ Load Model", id="engine-toggle-label", styles="content-align: center middle; padding: 1; height: 100%;")\n                        yield Switch(id="engine-toggle-switch")',
'yield Button("⚡ Load Model", id="toggle-engine-btn", variant="success")')

# Revert event handler back to Button.Pressed
content = content.replace('''    @on(Switch.Changed, "#engine-toggle-switch")
    def on_engine_toggle_switch(self, event: Switch.Changed) -> None:
        if getattr(self, "_ignore_switch_events", False):
            return
            
        if self.engine_port > 0 and is_port_in_use(self.engine_port):
            if not event.value: # if switch was turned off
                self.on_stop_engine_btn()
        else:
            if event.value: # if switch was turned on
                self.on_start_engine_btn()''',
'''    @on(Button.Pressed, "#toggle-engine-btn")
    def on_toggle_engine_btn(self) -> None:
        if self.engine_port > 0 and is_port_in_use(self.engine_port):
            self.on_stop_engine_btn()
        else:
            self.on_start_engine_btn()''')

# Revert update_status_bar logic
content = content.replace('''            toggle_switch = self.query_one("#engine-toggle-switch", Switch)
            toggle_lbl = self.query_one("#engine-toggle-label", Static)
            if self.engine_port <= 0:
                toggle_switch.display = False
                toggle_lbl.display = False
            else:
                toggle_switch.display = True
                toggle_lbl.display = True
                
                self._ignore_switch_events = True
                toggle_switch.value = server_online
                self._ignore_switch_events = False
                
                if server_online:
                    toggle_lbl.update("🛑 Unload Model")
                else:
                    toggle_lbl.update("⚡ Load Model")''',
'''            toggle_btn = self.query_one("#toggle-engine-btn", Button)
            if self.engine_port <= 0:
                toggle_btn.display = False
            else:
                toggle_btn.display = True
                if server_online:
                    toggle_btn.label = "🛑 Unload Model"
                    toggle_btn.variant = "error"
                else:
                    toggle_btn.label = "⚡ Load Model"
                    toggle_btn.variant = "success"''')

with open("rlm_optimized/tui_app.py", "w") as f:
    f.write(content)
