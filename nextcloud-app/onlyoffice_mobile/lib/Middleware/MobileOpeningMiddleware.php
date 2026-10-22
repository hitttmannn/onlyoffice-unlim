<?php
// SPDX-License-Identifier: AGPL-3.0-only
namespace OCA\OnlyofficeMobile\Middleware;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Middleware;
use OCP\AppFramework\Http\Response;
use OCP\AppFramework\Http\TemplateResponse;
use OCP\AppFramework\Http\RedirectResponse;
use OCP\IRequest;
use OCP\IUserSession;
use OCP\IGroupManager;
use OCP\IConfig;
use OCP\IURLGenerator;
use OCP\Files\IRootFolder;
use OCP\Files\File;
class MobileOpeningMiddleware extends Middleware {
    public function __construct(private IRequest $request,private IUserSession $users,
        private IGroupManager $groups,private IConfig $settings,
        private IURLGenerator $urls,private IRootFolder $root) {}
    public function afterController(Controller $controller,string $methodName,Response $response): Response {
        if (!($response instanceof TemplateResponse) || $response->getApp()!=='onlyoffice' || $response->getTemplateName()!=='editor') return $response;
        if (!preg_match('/Android|iPhone|iPad|iPod|Mobile/i',$this->request->getHeader('User-Agent'))) return $response;
        if ($this->settings->getAppValue('onlyoffice_mobile','mobile_default','yes')!=='yes') return $response;
        $params=$response->getParams();
        if (!empty($params['shareToken']) || !empty($params['isTemplate'])) return $response;
        try {
            $uid=$this->users->getUser()?->getUID();
            $fileId=(int)($params['fileId']??0);
            // Android direct-edit responses already validated the one-use core token.
            // Read the connector's signed reference; never pass it to the redirect URL.
            if (!empty($params['directToken'])) {
                $container=(new \OCP\AppFramework\App('onlyoffice'))->getContainer();
                [$data,$error]=$container->get(\OCA\Onlyoffice\Crypt::class)->readHash($params['directToken']);
                if (!$data || $data->action!=='direct') return $response;
                $uid=$data->userId;$fileId=(int)$data->fileId;
            }
            $allowed=json_decode($this->settings->getAppValue('onlyoffice_mobile','allowed_users','[]'),true);
            if (!$uid || (!$this->groups->isAdmin($uid) && (!is_array($allowed) || !in_array($uid,$allowed,true)))) return $response;
            $folder=$this->root->getUserFolder($uid);
            if ($fileId) {$found=$folder->getById($fileId);$file=$found[0]??null;}
            elseif (!empty($params['filePath'])) {$file=$folder->get($params['filePath']);}
            else return $response;
            if (!($file instanceof File) || !$file->isReadable() || !$file->isUpdateable() || !in_array(strtolower(pathinfo($file->getName(),PATHINFO_EXTENSION)),['docx','xlsx'],true)) return $response;
            // The target rechecks login, file ownership and connector edit permissions.
            // A fresh Android WebView may require a normal web login once.
            return new RedirectResponse($this->urls->linkToRoute('onlyoffice_mobile.mobile.index',['fileId'=>$file->getId()]));
        } catch (\OCP\Files\NotFoundException|\OCP\Files\NotPermittedException $e) {return $response;}
    }
}
