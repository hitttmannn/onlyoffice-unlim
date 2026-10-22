<?php
return ['routes'=>[
 ['name'=>'mobile#index','url'=>'/','verb'=>'GET'],
 ['name'=>'mobile#config','url'=>'/config/{fileId}','verb'=>'GET'],
 ['name'=>'mobile#revision','url'=>'/revision/{fileId}','verb'=>'GET'],
 ['name'=>'mobile#save','url'=>'/save/{fileId}','verb'=>'POST'],
]];
