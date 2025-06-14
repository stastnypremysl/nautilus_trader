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

//! Status report types for trading operations.
//!
//! This module provides report types for tracking and communicating the status
//! of various trading operations, including order fills, order status, position
//! status, and mass status requests.

pub mod fill;
pub mod mass_status;
pub mod order;
pub mod position;

// Re-exports
pub use fill::FillReport;
pub use mass_status::ExecutionMassStatus;
pub use order::OrderStatusReport;
pub use position::PositionStatusReport;
