# Security & Authentication Rule
- **Data Provisioning Security Rule**: 業務データ（CSV等）は、GitHub Pages等からクライアント側で直接Fetchしてはいけない。必ずGAS（v2_api）を経由し、認証を通過した状態で取得すること。
- **API Authentication**: APIへのすべてのアクセス（doPost / doGet）は、Tokenまたは適切な認証を通過しなければならない。
