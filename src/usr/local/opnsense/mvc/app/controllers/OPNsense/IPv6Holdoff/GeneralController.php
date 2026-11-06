<?php
namespace OPNsense\IPv6Holdoff;
class GeneralController extends \OPNsense\Base\IndexController {
    public function indexAction() {
        $this->view->pick('OPNsense/IPv6Holdoff/general');
        $this->view->generalForm = $this->getForm('general');
    }
}
