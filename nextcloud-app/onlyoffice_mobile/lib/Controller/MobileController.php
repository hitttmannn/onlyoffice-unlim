<?php
// SPDX-License-Identifier: AGPL-3.0-only
namespace OCA\OnlyofficeMobile\Controller;

use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;
use OCP\AppFramework\Http\TemplateResponse;
use OCP\AppFramework\Http\ContentSecurityPolicy;
use OCP\AppFramework\Http\Attribute\NoCSRFRequired;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\Files\File;
use OCP\Files\IRootFolder;
use OCP\IRequest;
use OCP\IUserSession;
use OCP\IGroupManager;
use OCP\IConfig;
use OCP\IURLGenerator;
use OCP\Http\Client\IClientService;

class MobileController extends Controller {
    private const GUID='asc.{9A38C060-94C7-4C39-B813-F5AA14661045}';
    public function __construct(string $appName,IRequest $request,
        private IUserSession $users,private IGroupManager $groups,
        private IRootFolder $root,private IConfig $settings,
        private IURLGenerator $urls,private IClientService $clients) {
        parent::__construct($appName,$request);
    }
    private function guard(): string {
        $uid=$this->users->getUser()?->getUID();
        $allowed=json_decode($this->settings->getAppValue('onlyoffice_mobile','allowed_users','[]'),true);
        if (!$uid || (!$this->groups->isAdmin($uid) && (!is_array($allowed) || !in_array($uid,$allowed,true)))) {
            throw new \OCP\AppFramework\OCS\OCSForbiddenException('Testing is restricted to administrators');
        }
        return $uid;
    }
    private function file(int $fileId): File {
        $folder=$this->root->getUserFolder($this->guard());
        $found=$folder->getById($fileId);
        if (!$found || !($found[0] instanceof File) || !$found[0]->isReadable() || !$found[0]->isUpdateable()) {
            throw new \OCP\AppFramework\OCS\OCSForbiddenException('File is not editable');
        }
        $file=$found[0];
        if (!in_array(strtolower(pathinfo($file->getName(),PATHINFO_EXTENSION)),['docx','xlsx'],true)) {
            throw new \InvalidArgumentException('Only DOCX and XLSX test copies are supported');
        }
        return $file;
    }
    private function oo() { return (new \OCP\AppFramework\App('onlyoffice'))->getContainer(); }
    private function docsUrl(): string {
        $url=$this->settings->getAppValue('onlyoffice_mobile','docs_url','');
        if (!$url || !in_array(parse_url($url,PHP_URL_SCHEME),['http','https'],true)) throw new \RuntimeException('Set onlyoffice_mobile docs_url');
        return rtrim($url,'/').'/';
    }
    private function route(string $action,int $fileId): string {
        return $this->urls->linkToRoute('onlyoffice_mobile.mobile.'.$action,['fileId'=>$fileId]);
    }
    #[NoAdminRequired]
    #[NoCSRFRequired]
    public function index(int $fileId=0): TemplateResponse|JSONResponse {
        try {$uid=$this->guard();} catch (\OCP\AppFramework\OCS\OCSForbiddenException $e) {return new JSONResponse(['error'=>'Access denied'],403);}
        if (!$fileId) {
            $files=[];
            foreach ($this->root->getUserFolder($uid)->getDirectoryListing() as $file) {
                if ($file instanceof File && $file->isUpdateable() && in_array(strtolower(pathinfo($file->getName(),PATHINFO_EXTENSION)),['docx','xlsx'],true)) {
                    $files[]=['name'=>$file->getName(),'url'=>$this->urls->linkToRoute('onlyoffice_mobile.mobile.index',['fileId'=>$file->getId()])];
                }
            }
            return new TemplateResponse('onlyoffice_mobile','list',['files'=>$files]);
        }
        try {$file=$this->file($fileId);} catch (\OCP\AppFramework\OCS\OCSForbiddenException $e) {return new JSONResponse(['error'=>'File access denied'],403);}
        $response=new TemplateResponse('onlyoffice_mobile','editor',[
            'title'=>$file->getName(),'docsUrl'=>$this->docsUrl(),
            'configUrl'=>$this->route('config',$fileId),'saveUrl'=>$this->route('save',$fileId),
            'revisionUrl'=>$this->route('revision',$fileId),
        ]);
        $csp=new ContentSecurityPolicy();
        $csp->addAllowedScriptDomain($this->docsUrl());
        $csp->addAllowedFrameDomain($this->docsUrl());
        $csp->addAllowedConnectDomain($this->docsUrl());
        $response->setContentSecurityPolicy($csp);
        return $response;
    }
    #[NoAdminRequired]
    #[NoCSRFRequired]
    public function config(int $fileId): JSONResponse {
        try {$this->file($fileId);} catch (\OCP\AppFramework\OCS\OCSForbiddenException $e) {return new JSONResponse(['error'=>'File access denied'],403);}
        $container=$this->oo();
        $response=$container->get(\OCA\Onlyoffice\Controller\EditorApiController::class)->config($fileId);
        $params=$response->getData();
        if (isset($params['error']) || empty($params['document']['key'])) return new JSONResponse(['error'=>'Connector refused configuration'],403);
        if (($params['editorConfig']['mode']??'edit')!=='edit' || ($params['document']['permissions']['edit']??false)!==true) return new JSONResponse(['error'=>'Editing is not permitted'],403);
        if (($params['document']['permissions']['copy']??true)===false || ($params['document']['permissions']['download']??true)===false) return new JSONResponse(['error'=>'Restricted-content documents are not supported by this panel'],403);
        if (($params['editorConfig']['customization']['plugins']??true)===false) return new JSONResponse(['error'=>'Plugins disabled by administrator'],403);
        $appConfig=$container->get(\OCA\Onlyoffice\AppConfig::class);
        $secret=$appConfig->getDocumentServerSecret();
        if (!$secret) return new JSONResponse(['error'=>'JWT must be configured'],503);
        unset($params['token']);
        $params['type']='desktop';
        $params['documentServerUrl']=$this->docsUrl();
        $plugins=$params['editorConfig']['plugins']??[];
        $plugins['pluginsData'][]=$this->docsUrl().'sdkjs-plugins/mobile-panel/config.json';
        $plugins['autostart'][]=self::GUID;
        $params['editorConfig']['plugins']=$plugins;
        $params['token']=\OCA\Onlyoffice\Vendor\Firebase\JWT\JWT::encode($params,$secret,'HS256');
        return new JSONResponse($params);
    }
    #[NoAdminRequired]
    #[NoCSRFRequired]
    public function revision(int $fileId): JSONResponse {
        try {$file=$this->file($fileId);} catch (\OCP\AppFramework\OCS\OCSForbiddenException $e) {return new JSONResponse(['error'=>'File access denied'],403);}
        return new JSONResponse(['revision'=>$file->getEtag()]);
    }
    #[NoAdminRequired]
    public function save(int $fileId): JSONResponse {
        try {$this->file($fileId);} catch (\OCP\AppFramework\OCS\OCSForbiddenException $e) {return new JSONResponse(['error'=>'File access denied'],403);}
        $validation=$this->config($fileId);
        if ($validation->getStatus()!==200) return $validation;
        $oo=$this->oo();
        $key=$oo->get(\OCA\Onlyoffice\KeyManager::class)->get($fileId);
        if (!$key) return new JSONResponse(['error'=>'No editing session'],409);
        $key=\OCA\Onlyoffice\DocumentService::generateRevisionId($key);
        $secret=$oo->get(\OCA\Onlyoffice\AppConfig::class)->getDocumentServerSecret();
        if (!$secret) return new JSONResponse(['error'=>'JWT missing'],503);
        $command=['c'=>'forcesave','key'=>$key];
        $command['token']=\OCA\Onlyoffice\Vendor\Firebase\JWT\JWT::encode($command+['iat'=>time(),'exp'=>time()+60],$secret,'HS256');
        $internal=$this->settings->getAppValue('onlyoffice_mobile','docs_internal_url','');
        if (!$internal) return new JSONResponse(['error'=>'Set docs_internal_url'],503);
        $response=$this->clients->newClient()->post(rtrim($internal,'/').'/command',[
            'headers'=>['Content-Type'=>'application/json'],'body'=>json_encode($command),'timeout'=>15,
            'nextcloud'=>['allow_local_address'=>true],
        ]);
        return new JSONResponse(json_decode($response->getBody(),true));
    }
}
