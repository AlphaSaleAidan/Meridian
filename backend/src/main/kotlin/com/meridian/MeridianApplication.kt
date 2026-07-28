package com.meridian

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class MeridianApplication

fun main(args: Array<String>) {
    runApplication<MeridianApplication>(*args)
}
