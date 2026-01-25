import os
import platform
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class Finding:
    severity: str  # "High", "Medium", "Low", "Info"
    category: str  # "System", "Network", "User", "Malware"
    title: str
    description: str
    recommendation: str

class SecurityAdvisor:
    def __init__(self):
        self.findings: List[Finding] = []
    
    def analyze_system_data(self, data: Dict[str, Any]):
        """Analyzes the raw system info data dictionary."""
        # Example Analysis Rules
        
        # 1. OS Check
        os_type = data.get('os_type', 'unknown')
        if os_type == 'linux':
             details = data.get('general', {}).get('details', {})
             distro = details.get('Distro', '')
             if 'Kali' in distro or 'Parrot' in distro:
                 self.add_finding("Info", "System", "Penetration Testing OS Detected", 
                                  f"The system '{distro}' is often used for security testing.", 
                                  "Ensure this system is authorized for use.")

        # 2. Memory Check (Example rule)
        mem = data.get('memory', {})
        total_gb = mem.get('total_gb', 0)
        if total_gb > 0 and total_gb < 4:
            self.add_finding("Low", "System", "Low Memory Detected",
                             f"Total memory is only {total_gb} GB.",
                             "Consider upgrading RAM for better forensic tool performance.")

        # 3. Swap Check
        if mem.get('swap_total') == "0.00M": # Example Check
             self.add_finding("Medium", "System", "No Swap Configured",
                              "Swap is disabled.",
                              "Enable swap to prevent OOM kills during heavy analysis.")

    def add_finding(self, severity, category, title, description, recommendation):
        self.findings.append(Finding(severity, category, title, description, recommendation))

    def generate_report(self) -> str:
        """Generates a simple HTML summary of findings."""
        if not self.findings:
            return "<p>No significant security findings based on current data.</p>"
        
        html = "<h2>Security Advisor - Plan of Attack/Defense</h2>"
        html += "<table class='findings-table'><tr><th>Severity</th><th>Category</th><th>Issue</th><th>Recommendation</th></tr>"
        
        severity_colors = {"High": "#ffcccc", "Medium": "#fff4cc", "Low": "#e6f3ff", "Info": "#f2f2f2"}

        for f in self.findings:
            bg_color = severity_colors.get(f.severity, "#ffffff")
            html += f"<tr style='background-color: {bg_color}'><td><b>{f.severity}</b></td><td>{f.category}</td><td><b>{f.title}</b><br>{f.description}</td><td>{f.recommendation}</td></tr>"
        
        html += "</table>"
        return html
