<?php
/*
Plugin Name: Aktien-Tool Hero Injector
Description: Injiziert die Aktien-Tool Buttons auf der Startseite via JS
*/
add_action('wp_footer', function() {
    if(get_the_ID() == 1045 || is_front_page()) {
        $html = '<section id="aktien-tool-buttons-hero" style="position:relative; z-index:99; max-width: 900px; margin: 40px auto 40px auto; padding: 30px; background-color: #ffffff; border: 1px solid #e1e8ed; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); font-family: sans-serif;"><h2 style="text-align: center; color: #0A2647; font-size: 28px; margin-bottom: 20px;">📊 Teste jetzt meine kostenlosen Aktientools</h2><p style="font-size: 17px; line-height: 1.6; text-align: center; max-width: 700px; margin: 0 auto 25px; color: #334155;">🔍 <strong>Aktien-Analyse:</strong> Dividendenrendite, KGV, KUV, Gewinnwachstum – automatisch generiert.<br>⚖️ <strong>Aktien-Vergleich:</strong> Lass Top-Werte automatisch gegeneinander antreten!<br>🧠 Ideal für Einsteiger und Fortgeschrittene.</p><div style="text-align: center; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;"><a href="https://schatzsuche40.de/aktien-tool/" style="display: inline-block; padding: 15px 30px; background-color: #0d6efd; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 6px rgba(13, 110, 253, 0.2);">🚀 Aktien-Analyse</a><a href="https://schatzsuche40.de/aktien-vergleichstool/" style="display: inline-block; padding: 15px 30px; background-color: #10b981; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);">⚖️ Aktien-Vergleich</a></div></section>';
        echo "<script>document.addEventListener('DOMContentLoaded', function() { var target = document.querySelector('#Content') || document.querySelector('.mcb-section') || document.body; var div = document.createElement('div'); div.innerHTML = '" . addslashes($html) . "'; target.parentNode.insertBefore(div.firstChild, target); });</script>";
    }
});
