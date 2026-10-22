<?php
// SPDX-License-Identifier: AGPL-3.0-only
namespace OCA\OnlyofficeMobile\AppInfo;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
use OCP\AppFramework\Bootstrap\IBootContext;
class Application extends App implements IBootstrap {
    public function __construct(array $urlParams=[]) {parent::__construct('onlyoffice_mobile',$urlParams);}
    public function register(IRegistrationContext $context): void {
        $context->registerMiddleware(\OCA\OnlyofficeMobile\Middleware\MobileOpeningMiddleware::class,true);
    }
    public function boot(IBootContext $context): void {}
}
