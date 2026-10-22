<?php // SPDX-License-Identifier: AGPL-3.0-only ?>
<div id="app-content"><div id="app-content-wrapper" style="padding:24px;display:block;width:100%;min-width:0"><h2>Простые документы — тестовый режим</h2><p>Доступно только администраторам. Используйте копии файлов в корне ваших «Файлов».</p><p>В Word изменяемый абзац может терять оформление. Другие документы и стандартный редактор не меняются.</p><ul style="display:block">
<?php foreach ($_['files'] as $file) { ?><li style="display:block;margin:12px 0"><a href="<?php p($file['url']); ?>"><?php p($file['name']); ?></a></li><?php } ?>
</ul></div></div>
