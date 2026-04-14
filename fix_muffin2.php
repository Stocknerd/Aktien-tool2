<?php
require_once('/www/htdocs/w01b3188/schatzsuche40.de/wp-load.php');
$post_id = 1045;
$meta = get_post_meta($post_id, 'mfn-page-items', true);
$was_encoded = false;
if(is_string($meta) && !empty($meta)) {
    $decoded = base64_decode($meta, true);
    if($decoded !== false && is_serialized($decoded)) {
        $meta = unserialize($decoded);
        $was_encoded = true;
    }
}
if(is_array($meta)) {
    // Remove existing herosection123 if any
    $meta = array_values(array_filter($meta, function($sec) {
        return !(isset($sec['uid']) && $sec['uid'] === 'herosection123');
    }));

    $html_content = '<section style="max-width: 900px; margin: 40px auto 40px auto; padding: 30px; background-color: #ffffff; border: 1px solid #e1e8ed; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); font-family: sans-serif;">
  <h2 style="text-align: center; color: #0A2647; font-size: 28px; margin-bottom: 20px;">
    📊 Teste jetzt meine kostenlosen Aktientools
  </h2>
  <p style="font-size: 17px; line-height: 1.6; text-align: center; max-width: 700px; margin: 0 auto 25px; color: #334155;">
    🔍 <strong>Aktien-Analyse:</strong> Dividendenrendite, KGV, KUV, Gewinnwachstum – automatisch generiert.<br>
    ⚖️ <strong>Aktien-Vergleich:</strong> Lass Top-Werte automatisch gegeneinander antreten!<br>
    🧠 Ideal für Einsteiger und Fortgeschrittene.
  </p>
  <div style="text-align: center; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">
    <a href="https://schatzsuche40.de/aktien-tool/" style="display: inline-block; padding: 15px 30px; background-color: #0d6efd; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 6px rgba(13, 110, 253, 0.2);">
      🚀 Aktien-Analyse
    </a>
    <a href="https://schatzsuche40.de/aktien-vergleichstool/" style="display: inline-block; padding: 15px 30px; background-color: #10b981; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);">
      ⚖️ Aktien-Vergleich
    </a>
  </div>
</section>';

    $new_section = array(
        'icon' => 'section',
        'jsclass' => 'section',
        'title' => 'Section',
        'uid' => 'herosection123',
        'attr' => array('padding_top' => '0px', 'padding_bottom' => '0px'),
        'ver' => 'default',
        'wraps' => array(
            array(
                'icon' => 'wrap',
                'size' => '1/1',
                'jsclass' => 'wrap',
                'uid' => 'herowrap123',
                'title' => 'Wrap',
                'items' => array(
                    array(
                        'type' => 'html',
                        'jsclass' => 'html',
                        'title' => 'HTML',
                        'icon' => 'html',
                        'uid' => 'herocolumn123',
                        'size' => '1/1',
                        'attr' => array(),
                        'fields' => array(
                            'content' => $html_content
                        )
                    )
                )
            )
        )
    );
    
    array_unshift($meta, $new_section);
    
    if($was_encoded) {
        $updated = base64_encode(serialize($meta));
    } else {
        $updated = $meta;
    }
    
    update_post_meta($post_id, 'mfn-page-items', $updated);
    echo "Muffin settings updated with html correctly.\n";
} else {
    echo "Could not parse muffin array.\n";
}
?>
