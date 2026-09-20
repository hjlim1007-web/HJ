package com.hj.naverlauncher

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.widget.Toast

/**
 * 앱 아이콘을 누르면 UI 없이 크롬 앱을 실행하고 그 안에서 네이버를 연 뒤 스스로 종료한다.
 *
 * 크롬이 설치돼 있지 않거나 비활성화된 경우에는 패키지를 지정하지 않은 VIEW 인텐트로
 * 폴백해 기본 브라우저가 열도록 한다.
 */
class MainActivity : Activity() {

    private companion object {
        const val TARGET_URL = "https://www.naver.com"

        /** 정식판을 먼저, 그다음 베타/개발자판/카나리 순으로 찾는다. */
        val CHROME_PACKAGES = listOf(
            "com.android.chrome",
            "com.chrome.beta",
            "com.chrome.dev",
            "com.chrome.canary"
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        openNaver()
        finish()
    }

    private fun openNaver() {
        val uri = Uri.parse(TARGET_URL)

        installedChromePackage()?.let { pkg ->
            val intent = Intent(Intent.ACTION_VIEW, uri).apply {
                setPackage(pkg)
                addCategory(Intent.CATEGORY_BROWSABLE)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            try {
                startActivity(intent)
                return
            } catch (e: ActivityNotFoundException) {
                // 패키지는 있지만 VIEW 를 처리할 액티비티가 없는 드문 경우 → 아래 폴백으로.
            }
        }

        openWithAnyBrowser(uri)
    }

    /** 설치돼 있고 활성화된 크롬 패키지를 찾는다. 없으면 null. */
    private fun installedChromePackage(): String? =
        CHROME_PACKAGES.firstOrNull { pkg ->
            try {
                packageManager.getApplicationInfo(pkg, 0).enabled
            } catch (e: PackageManager.NameNotFoundException) {
                false
            }
        }

    private fun openWithAnyBrowser(uri: Uri) {
        val intent = Intent(Intent.ACTION_VIEW, uri).apply {
            addCategory(Intent.CATEGORY_BROWSABLE)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            startActivity(intent)
            Toast.makeText(this, R.string.chrome_not_found, Toast.LENGTH_SHORT).show()
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(this, R.string.no_browser, Toast.LENGTH_LONG).show()
        }
    }
}
