/* Carry an explicit theme choice across pages without any storage:
   once the reader presses the theme toggle (or arrives with ?theme=), every
   same-site link they click gets ?theme=light|dark appended. Injected by site/build.py. */
(function(){
  var r=document.documentElement, chosen=null;
  try{var t=new URLSearchParams(location.search).get('theme');if(t==='light'||t==='dark')chosen=t}catch(e){}
  var tg=document.getElementById('themeToggle');
  if(tg)tg.addEventListener('click',function(){chosen=r.getAttribute('data-theme')});
  function withTheme(h){
    var hash='',i=h.indexOf('#');if(i>=0){hash=h.slice(i);h=h.slice(0,i)}
    h=h.replace(/([?&])theme=(light|dark)(&|$)/,'$1').replace(/[?&]$/,'');
    return h+(h.indexOf('?')>=0?'&':'?')+'theme='+chosen+hash;
  }
  document.addEventListener('click',function(e){
    if(!chosen)return;
    var a=e.target.closest&&e.target.closest('a[href]');if(!a)return;
    var h=a.getAttribute('href');
    if(a.hasAttribute('download')||a.target==='_blank'||/^(#|[a-z]+:|\/\/)/i.test(h))return;
    a.setAttribute('href',withTheme(h));
  },true);
})();
