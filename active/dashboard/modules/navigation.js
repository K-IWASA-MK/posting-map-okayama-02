var pageIdMap = {
  'page-areas': 'areas',
  'page-settings': 'settings',
  'page-ranking': 'ranking',
  'page-storage-register': 'storage-register',
  'page-storage-list': 'storage-list',
  'page-bulletin': 'bulletin'
};

let _prevPageBeforeTier2 = 'areas';
var lastAreaSubPage = 'areas';
var scrollPositions = { areas: 0, settings: 0, ranking: 0 };

function toggleNavTier(tier) {
  if (tier === 2) {
    const activePage = document.querySelector('.page:not(.hidden)');
    if (activePage) {
      _prevPageBeforeTier2 = pageIdMap[activePage.id] || 'areas';
    }
    (typeof switchPage === 'function' ? switchPage : window.switchPage)('areas');
  }
}

function backToTier1() {
  const targetPage = _prevPageBeforeTier2 || 'settings';
  (typeof switchPage === 'function' ? switchPage : window.switchPage)(targetPage);
}

function navigateToAreaTab() {
  const target = window.lastAreaSubPage || lastAreaSubPage || 'areas';
  (typeof switchPage === 'function' ? switchPage : window.switchPage)(target);
}

function updateBottomNavVisibility() {
  const nav = document.getElementById('bottom-nav');
  const hasUser = typeof localStorage !== 'undefined' && !!localStorage.getItem('user_info');
  if (nav) nav.style.display = hasUser ? '' : 'none';
}

window.pageIdMap = pageIdMap;
window.scrollPositions = scrollPositions;
window.lastAreaSubPage = lastAreaSubPage;
window.toggleNavTier = toggleNavTier;
window.backToTier1 = backToTier1;
window.navigateToAreaTab = navigateToAreaTab;
window.updateBottomNavVisibility = updateBottomNavVisibility;
