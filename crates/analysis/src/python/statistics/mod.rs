// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

//! Python bindings for trading performance statistics.

pub mod expectancy;
pub mod long_ratio;
pub mod loser_avg;
pub mod loser_max;
pub mod loser_min;
pub mod profit_factor;
pub mod returns_avg;
pub mod returns_avg_loss;
pub mod returns_avg_win;
pub mod returns_volatlity;
pub mod risk_return_ratio;
pub mod sharpe_ratio;
pub mod sortino_ratio;
pub mod win_rate;
pub mod winner_avg;
pub mod winner_max;
pub mod winner_min;

use std::collections::BTreeMap;

use nautilus_core::UnixNanos;

fn transform_returns(raw_returns: BTreeMap<u64, f64>) -> BTreeMap<UnixNanos, f64> {
    raw_returns
        .keys()
        .map(|&k| (UnixNanos::from(k), raw_returns[&k]))
        .collect()
}
